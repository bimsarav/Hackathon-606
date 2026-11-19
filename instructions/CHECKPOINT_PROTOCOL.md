# Checkpoint Protocol (write-ahead)

Goal: a session can stop at ANY moment (tokens exhausted, crash, closed terminal), and the next session resumes without losing or repeating work.

## Rule 1: Plan before acting
Before a task starts, `execution/CURRENT_TASK.md` must list its steps as a checklist with stable IDs:
```
- [x] T-002.1 Read inbox files              (done, verified)
- [~] T-002.2 Move files to subfolders      (STARTED: may be partial)
- [ ] T-002.3 Write requirements-analysis.md
```

## Rule 2: Mark started BEFORE doing
Before running a step, change it to `[~]` and append to `execution.log`:
`<timestamp> | <step-id> | STARTED | <intended action> | <files to touch>`

## Rule 3: Mark done AFTER verifying
After the step's result has been checked (file exists, test ran, command output OK), change it to `[x]` and append:
`<timestamp> | <step-id> | DONE | <result> | <how verified>`
Then update `NEXT_ACTION.md` to point at the next step.

## Rule 4: Keep steps small and idempotent
Each step should take at most a few minutes of work and be safe to re-run. Examples: "write file X", "run test suite Y", "move files A, B and C". Break big work (for example "build the backend") into many steps.

## Rule 5: Write file-by-file
When generating many files, write each file completely in one go. If interrupted, a partially written file shows up as missing or truncated, and the step is re-run.

## Recovery on resume
| Found in CURRENT_TASK | Meaning | Action |
|---|---|---|
| All `[x]`, NEXT_ACTION set | Clean stop | Start NEXT_ACTION |
| One `[~]` | Interrupted mid-step | Check the files that step touches. If its outcome is fully present, mark `[x]` and log `DONE (recovered)`. Otherwise redo the step (steps are idempotent). |
| Log and files disagree | Inconsistent state | Trust the actual files. Fix the tracking files, log the discrepancy in `errors.log`, then continue. |

## Before running low on budget
If a session looks like it is ending, or the user says STOP: finish or roll back the current step, sync all tracking files, and write the session report.
Rules 1–3 already guarantee recovery if this isn't possible.
