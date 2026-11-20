# Checkpoint Protocol (write-ahead, low-token resume)

Goal: a session can stop at ANY moment (lost internet connection, tokens exhausted, crash, restart, closed terminal). The next session resumes **cheaply**, without losing or repeating work and without re-reading large files.

## 0. Three layers of logging
| Layer | Written by | File | Purpose |
|---|---|---|---|
| **Automatic** | Claude Code hooks (`.claude/settings.json` → `.claude/hooks/checkpoint_hook.py`), zero token cost | `execution/logs/tool-activity.log` (every tool call: time, session, ok/FAIL, tool, file or command, secrets redacted; committed, rotates at 2 MB) · `execution/logs/sessions.log` (SessionStart, TurnEnd, **TurnFailed** = API/connection error, PreCompact, SessionEnd) | Shows exactly what happened up to the interruption, even if no manual checkpoint was written |
| **Snapshot** | Claude, at every step change | `execution/RESUME.md` (≤ 40 lines, overwritten, never appended) | The **only** file a resume normally needs. Injected into context automatically at session start by the SessionStart hook |
| **Journal** | Claude | `execution/CURRENT_TASK.md` (step checklist with file manifests) · `execution/logs/execution.log` (STARTED/PROGRESS/DONE) · `execution/logs/errors.log` · `execution/logs/decisions.log` · `execution/logs/output/` (saved output of long commands, committed after trimming, see §5) | Detail used only when the snapshot is not enough or disagrees with reality |

## 1. Plan before acting
Before a task starts, `CURRENT_TASK.md` lists its steps with stable IDs. A step that creates several files gets a **file manifest**, so an interruption mid-step only redoes the missing files:
```
- [~] T-004.3 Order service CRUD                       (STARTED)
      files: [x] OrderController.java [x] OrderService.java [ ] OrderRepository.java [ ] OrderServiceTest.java
- [ ] T-004.4 Order events to Kafka
```

## 2. Mark started BEFORE doing
Set the step to `[~]`, update `RESUME.md` ("In progress"), and append to `execution.log`:
`<UTC timestamp> | <step-id> | STARTED | <intended action> | <files to touch>`

## 3. Log progress INSIDE long steps
After each file of a manifest, or each sub-action of a long step, tick it in the manifest and append:
`<UTC timestamp> | <step-id> | PROGRESS | <what is done> | <file>`
Rule of thumb: never more than ~5 minutes or ~3 files of work without a written checkpoint.

## 4. Mark done AFTER verifying
Once the result is checked (file exists and is complete, build or test ran, output OK), set the step to `[x]`, append
`<UTC timestamp> | <step-id> | DONE | <result> | <how verified>`, then update `NEXT_ACTION.md` and **rewrite `RESUME.md`**.

## 5. Long-running commands (builds, image pulls, test suites, stacks)
- Run them with output saved to a file: `cmd > execution/logs/output/<step-id>-<name>.log 2>&1` (or `run_in_background`), and record the path, PID or container names and expected duration in `RESUME.md` under "Running / last long command".
- On resume, **read the saved output's tail** to decide: finished OK → mark done; failed → fix; still running → wait. Never blindly re-run a 10-minute build.
- Record results in one line in `execution.log` (exit code, duration, test counts), not the full output.
- Saved output is committed with the run, so keep it small and clean: when the step is DONE, trim each file to its last 300 lines (`tail -n 300 f > f.tmp && mv f.tmp f`), and never save commands that print secrets (env dumps, tokens).

## 6. Small, idempotent, complete-on-write
- Each step takes a few minutes at most and is safe to re-run.
- Write each file completely in one Write call. A file cut off by an interruption is detected (missing or truncated, unbalanced braces, no closing tag) and rewritten.
- Prefer create-if-missing and upsert operations; destructive operations (drop, rm, reset) are logged in `execution.log` BEFORE they run.

## 7. RESUME.md format (keep ≤ 40 lines; overwrite at every step change)
```
# RESUME (updated <UTC timestamp>)
Product: <name or n/a> · Phase: <n> · Task: <id + title>
Stack: <selected stack, route (menu option n / user-specified / autonomous), link to TECH_STACK.md> or "not selected yet"
Last DONE: <step-id> <one line>
In progress: <step-id> <one line> · partial state: <files done / remaining>
Next: 1) <exact action> 2) <...> 3) <...>
Running / last long command: <cmd> → <output file> (<status>)
Environment: <ports, containers, versions, where creds live (never values)>
Open questions / blockers: <ids>
Do NOT redo: <expensive things already done and verified>
```

## 8. Resume procedure (cheapest path first)
1. Read the injected snapshot (or `execution/RESUME.md`) plus the injected tail of `tool-activity.log` and `sessions.log`.
2. If the last activity lines match the snapshot's "In progress" step, check **only the files that step touches** (and the saved output of any long command), then continue.
3. Only if they disagree or the snapshot is stale, read `CURRENT_TASK.md`, the last 20 lines of `execution.log` and `errors.log`, then reconcile.

| Found | Meaning | Action |
|---|---|---|
| Snapshot says DONE, nothing in progress | Clean stop | Start "Next" item 1 |
| A step is `[~]` | Interrupted mid-step | Check its manifest or files. Complete parts are kept; redo only missing or truncated parts. Log `DONE (recovered)` |
| `sessions.log` ends with `TurnFailed` | API or connection error mid-turn | The last `tool-activity` lines show the final action. Verify its effect before redoing it |
| Activity after the last checkpoint | Work done but not checkpointed | Verify those files and commands, then write the missing checkpoint |
| Log and files disagree | Inconsistent | Trust the files; fix the tracking files; log the discrepancy in `errors.log` |

## 9. Log lifecycle: one product run = one set of logs
- **During a product run (unfinished work):** everything in `execution/logs/` and the tracking files in `execution/` is **committed** with the work, so a resume on any machine or clone has the full history.
- **At delivery (or when a product is dropped):** after the final commit of the product, run
  `scripts/archive-product-logs.sh <product-name> --status delivered|dropped --yes`.
  It **moves** all logs (including the activity log and saved output) and a snapshot of the tracking files to `execution/archive/<product-name>-<UTC stamp>/`, with a checksummed `ARCHIVE.md` manifest, then resets the logs to empty and the tracking files from `execution/templates/`.
- `execution/archive/` is **git-ignored**: archives are kept locally and never committed. Commit the resulting reset (empty logs, fresh tracking files) as the start of the next product run.
- Every product run therefore **starts with empty logs**. Never append a new product's work to an old run's logs.

## 10. Before running low on budget, or on STOP
Finish or roll back the current step, rewrite `RESUME.md`, and sync the tracking files. Rules 1–5 plus the automatic hooks already guarantee recovery if this isn't possible.
