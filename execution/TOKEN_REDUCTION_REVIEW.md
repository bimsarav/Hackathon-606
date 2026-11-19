# Token Reduction Review: next product build

Date: 2026-11-19 · Scope: read-only review of the workspace (CLAUDE.md, instructions/, execution/, .claude/, scripts/, input/inbox/) plus the main agent's account of attempts 1–3.
Estimates are rough orders of magnitude, not measurements: `tool-activity.log` and `sessions.log` are empty in both the live logs and the archived run, so no per-call data exists. Items marked **(verify)** rely on Claude Code behaviour I am not certain of.

## 1. What the workspace already does well
- `CLAUDE.md` on disk (24 lines) already uses a "cheapest path first" resume: the SessionStart hook injects `RESUME.md` (capped at 6,000 chars) plus the last 15 activity and 5 session lines. `MASTER_PROMPT.md` (476 lines, about 6–7k tokens) is read only when a rule is unclear.
- CHECKPOINT_PROTOCOL §5 already says to save long command output to `execution/logs/output/` and read only its tail.
- The hooks themselves cost no tokens, because they write to files and not to context.

## 2. Where the tokens actually go (diagnosis)
| Cost driver | Why it is expensive | Seen in |
|---|---|---|
| **Throw-away work** (stack change, user reset) | The whole emitted output is lost and paid for again. Output tokens are the most expensive kind | Attempts 1→2→3: the shared library was written twice and deleted twice; the Python build was discarded |
| **LLM-written boilerplate** | About 10 services × 10–15 near-identical files (build file, Application, config, Dockerfile, Flyway, tests) | All attempts |
| **Re-deriving facts** | curl against Maven Central and Docker Hub, BOM inspection, trial-and-error on Spring Boot 4, Jackson 3 and Testcontainers 2 names, and Docker socket/uid fixes, repeated every attempt | Attempts 2–3 |
| **Verbose tool output** | Gradle, Docker and npm print thousands of lines. Each full test rerun can put 5–30k tokens into context, and that text is then re-sent (from cache) on every later turn | Attempt 1 |
| **Many small turns** | Every tool call re-sends the whole context. Caching makes this cheaper, not free. The checkpoint protocol adds 3–5 tracking-file edits per step | All |
| **Long prose** | About 15 docs written by hand, plus long progress and summary messages | Attempt 1 |
| **Unbriefed subagent** | It rebuilt the frontend from scratch with no template or facts: about 240k tokens | Attempt 1 |

The first two rows (rework and boilerplate) are probably more than half the spend. Fix them first.

## 3. Recommendations, ranked by saving ÷ effort

Saving scale: XL > 200k tokens per product, L 50–200k, M 10–50k, S < 10k. Effort: T trivial (< 15 min), L low (< 1 h), M medium (1–3 h, or done once during the next run).

| # | Recommendation | Saving | Effort | Ratio |
|---|---|---|---|---|
| R1 | Settle the stack, scope and environment once, before any code | XL | T | ★★★★★ |
| R2 | WIP commits to a branch so a reset cannot destroy work | XL | T | ★★★★★ |
| R3 | Persistent `KNOWN_FACTS.md` environment cache | L | T | ★★★★★ |
| R4 | Quiet build/test wrapper script that prints only a summary | L | L | ★★★★ |
| R5 | Cap shell output in settings | M | T | ★★★★ |
| R6 | Toolkit of templates outside `products/` + a service generator script | XL | M | ★★★★ |
| R7 | "Token discipline" rules in CLAUDE.md (no re-reads, Edit not rewrite, short messages) | M | T | ★★★★ |
| R8 | MVP slice first; docs last and generated from code | L | L | ★★★ |
| R9 | Checkpoint helper script plus lighter tracking cadence | M–L | L | ★★★ |
| R10 | Session hygiene: fresh session per phase or service; `/compact` with focus | M–L | T | ★★★ |
| R11 | Skills and slash commands for repeated procedures | M | L | ★★★ |
| R12 | Subagent policy: when to use, brief size, model per task | L (or a loss if misused) | L | ★★★ |
| R13 | Incremental tests plus Gradle and Docker caches | M | L | ★★ |
| R14 | Guard-rail hooks (block unbounded builds and huge reads) | M | M | ★★ |
| R15 | Workflow / multi-agent fan-out: only after R6 exists | ± | M | ★ |

### R1. Settle the stack, scope and environment once, before any code
- **What:** At the end of Phase 1, send ONE grouped question set and record the answers in `execution/DECISIONS.md` before Phase 4:
  - language and JDK
  - build tool
  - service list and MVP cut (R8)
  - frontend scope
  - target disk/RAM budget: the host has **42 GB free (91% used)**, and about 10 JVM images plus Kafka plus Postgres will use a large part of that
  - whether WIP commits are allowed (R2)
  - which docs are mandatory
  - "is this stack final?"

  Add a rule: "No code before DEC-stack is approved."
- **Saving:** XL. Attempts 1 and 2 were each discarded after a stack change. One avoided restart saves 100–300k+ tokens.
- **Risk:** The user may still change their mind. That is cheap if R2 and R6 are in place.
- **Next step:** Add a "Phase-1 gate questionnaire" (about 10 lines) to `instructions/PRODUCT_RULES.md` §5. Add `DEC-stack` as a required row in `execution/templates/DECISIONS.md`.

### R2. WIP commits to a branch so a reset cannot destroy work
- **What:** The default rule is "commit only when the user asks". Ask for a standing permission instead: after each DONE step, `git add products/<name> execution && git commit -m "wip(<step-id>)"` on a `wip/<product>` branch. A `git checkout -- . && rm -rf` by the user then leaves the work recoverable (`git log wip/...`). A lighter option is `git stash push -u -m <step>` before any destructive request.
- **Saving:** XL in the bad case. The 35-file library (about 60–100k output tokens) was lost twice. After R6, the library lives in `toolkit/` anyway.
- **Risk:** Noisy history. Fix it by squashing at delivery. Secrets must never be committed: the `.gitignore` already covers `.env`.
- **Next step:** Add one line under "While working" in `CLAUDE.md`, recording the user's standing approval with its date.

### R3. Persistent `KNOWN_FACTS.md` environment cache
- **What:** A file (≤ 80 lines) of *verified* facts, each with a date and how it was verified:
  - JDK 27 + Gradle 9.9.1 image `gradle:9.9.1-jdk27`
  - Spring Boot / Spring Cloud / Kafka / Testcontainers versions
  - Spring Boot 4 starter names
  - Jackson 3 packages (`tools.jackson.*`)
  - Testcontainers 2 artifact names
  - the Docker socket/uid fix (`--group-add $(stat -c %g /var/run/docker.sock)` or equivalent)
  - Docker 20.10 / Compose 2.21 limits
  - disk budget
  - image tags for Postgres, Kafka (KRaft), Node and Playwright

  Rule: "Read KNOWN_FACTS before any version lookup; only research what is missing, then append it."
- **Placement:** It must survive `archive-product-logs.sh`. That script only moves the `TRACKING` list and `logs/`, so `execution/KNOWN_FACTS.md` would survive, but `toolkit/KNOWN_FACTS.md` (R6) is clearer.
- **Saving:** L. Each research round (curl, BOM inspection, failed compile on wrong names) is about 10–40k. It recurred in every attempt and in many sessions.
- **Risk:** Stale facts. Fix it by giving each line a "verified YYYY-MM-DD" stamp, and re-checking only the JDK/Boot GA at product start (PRODUCT_RULES §3 requires this anyway).
- **Next step:** Create the file now from the facts the main agent already knows (the main agent has them in its context; I don't), and reference it from `CLAUDE.md`.

### R4. Quiet build/test wrapper script
- **What:** Add `scripts/dbuild.sh <step-id> <gradle-args…>`. It runs the Gradle container with `--console=plain -q --warning-mode=none`, mounts the socket, uid fix and cache volume from KNOWN_FACTS, and writes the full log to `execution/logs/output/<step-id>.log`. It prints only:
  - the exit code and duration
  - `BUILD SUCCESSFUL/FAILED`
  - the test totals, parsed from `build/test-results/**/*.xml`
  - the first 20 compiler errors (`grep -m20 'e: \|error:'`)
  - the names and first lines of failing tests

  Add the same pattern for `npm`/Playwright (`--reporter=line`) and `docker compose up` (show only `ps` health).
- **Saving:** L. A full multi-module test run printed raw is 5–30k tokens. Summarised, it is under 500. Over about 30–60 runs per product, that is 150k+. It also keeps the context small, so every later turn is cheaper.
- **Risk:** Hidden context on unusual failures. The full log is one `sed -n`/`grep` away.
- **Next step:** Write `scripts/dbuild.sh` (about 40 lines) and `scripts/test-summary.py` (JUnit XML → 10 lines). Reference both in KNOWN_FACTS and CLAUDE.md.

### R5. Cap shell output in settings
- **What:** Set `"env": {"BASH_MAX_OUTPUT_LENGTH": "15000"}` in `.claude/settings.json`. This is the setting the task calls `bashOutputMaxChars`; in Claude Code it is an environment variable **(verify the exact name and default with `/config` or the docs)**. Optionally also set `MAX_MCP_OUTPUT_TOKENS`. This is a safety net for when R4 is bypassed.
- **Saving:** M (it removes the long tail of accidental 50k-char dumps, such as the SQL profiling output).
- **Risk:** Truncated output can hide the error. Output is usually truncated in the middle, so the end stays visible **(verify)**.
- **Next step:** Add an `env` block to `.claude/settings.json`.

### R6. Toolkit of templates + a service generator script
- **What:** Create `toolkit/` at the workspace root. It is AI working material, never delivered, and is *copied* into each product:
  - `toolkit/gradle/`: wrapper, `settings.gradle.kts` skeleton, `libs.versions.toml`, `build-logic/` convention plugins (`java-service`, `java-library`, `spring-boot-service`, `testcontainers`)
  - `toolkit/common-lib/`: the shared library (errors, problem+json, security/JWT, Kafka envelope, audit, paging, test fixtures). This is the 35-file library that was lost twice
  - `toolkit/service-template/`: Application, config, Flyway V1, Dockerfile, health test and a Testcontainers base test, with `__SERVICE__`, `__PORT__`, `__DB__` and `__PKG__` placeholders
  - `toolkit/frontend-template/` (Vite + React + TS + Playwright config) and `toolkit/compose/` fragments
  - `scripts/new-service.sh <name> <port> <db>`: `cp -r` plus `sed` substitutions plus registration in `settings.gradle.kts` and compose

  The LLM then writes only domain code: entities, endpoints, events and tests.
- **Bootstrapping:** Do not build the toolkit separately. In the next run, write the first service and common-lib *into* `toolkit/` (generic), compile them once, then generate every service from them. Later products reuse the toolkit unchanged.
- **Saving:** XL. About 10 services × about 10 boilerplate files × about 1.5k tokens is about 150k output tokens per product, plus the library re-emits. Fewer compile-fix loops, because the template is already known to compile.
- **Risk:** The template drifts from the mandated latest versions. Keep versions only in `libs.versions.toml`, which is bumped per product. PRODUCT_RULES §1 says only `input/`, `instructions/`, `execution/` and `CLAUDE.md` stay at the root, so `toolkit/` and `scripts/` need an explicit exception. Delivery is unaffected because files are copied.
- **Next step:** Amend PRODUCT_RULES §1 ("`toolkit/` and `scripts/` are AI working files, never delivered") and add `toolkit/README.md` (10 lines: what each part is and the generator usage).

### R7. "Token discipline" rules in CLAUDE.md
Add about 8 lines (CLAUDE.md stays under 40 lines, which is fine: it is re-sent every turn, so keep it short):
- Do not re-read a file after Write/Edit. Use Edit for changes, never a full rewrite or re-emit.
- Do not write large files with heredocs and then `cat` them back. Use one Write per file.
- Read big inputs selectively: `esmp_sample_dump.sql` is 1,294 lines, so use `grep`/`head`, never a full read.
- Progress messages: ≤ 3 lines. The session report: 5 labelled lines (MASTER_RULES "Session report").
- No research that KNOWN_FACTS answers. No rerun of a verified step (`Do NOT redo` in RESUME.md).
- Batch independent tool calls in one turn.

**Saving:** M (about 10–30k per session). **Risk:** none. **Next step:** Edit `CLAUDE.md`.

### R8. MVP slice first; docs last and generated from code
- **What:**
  - (a) Propose an MVP cut in the R1 questionnaire. For example, build the core domain services and gateway end-to-end first (vertical slice: one entity → REST → Kafka event → UI page → Playwright test). Add the remaining services from the generator afterwards.
  - (b) OpenAPI comes from springdoc (export `openapi.json` with one Gradle task, not handwritten).
  - (c) Docs are written once, in Phase 7, as a fixed set: README, architecture + ADR index, test report from R4's summaries, and `CONFLUENCE_PAGE.md`. Do not write a separate markdown file per department. The master prompt's "Do not generate duplicate documentation" already supports this.
  - (d) Diagrams are ASCII, once, reused in README and Confluence.
- **Saving:** L. Attempt 1's about 15 docs were roughly 40–80k output tokens. The MVP-first slice avoids rework when requirements change mid-build.
- **Risk:** It must still meet PRODUCT_RULES §4 "Done". The MVP is an order of work, not a smaller delivery, unless the user approves a smaller scope.
- **Next step:** Add "Docs: Phase 7 only, list = …" to `instructions/DOCUMENTATION_RULES.md` (6 lines now). Add an "MVP slice" step to the Phase-3 plan template.

### R9. Checkpoint helper script plus lighter tracking cadence
- **What:** The protocol touches RESUME, CURRENT_TASK, execution.log, NEXT_ACTION and PROJECT_STATUS at many steps. That is 3–5 tool turns of overhead per step, each re-sending the whole context. Two changes:
  - `scripts/ckpt.sh <step-id> STARTED|PROGRESS|DONE "<msg>" [file]` appends to `execution.log` and flips `[ ]`/`[~]`/`[x]` in `CURRENT_TASK.md` with `sed`: one Bash call instead of 2–3 Edits.
  - Update `NEXT_ACTION.md`/`PROJECT_STATUS.md` only at task or phase boundaries. RESUME.md already carries "Next".

  Keep the RESUME.md rewrite at each step change (it is the resume anchor).
- **Saving:** M–L. Possibly 20–30% fewer tool turns over a 300-turn build.
- **Risk:** Resumability is unchanged if RESUME and execution.log are still written before and after each step. The script must be idempotent.
- **Next step:** Write `scripts/ckpt.sh`. Edit CHECKPOINT_PROTOCOL §2–4 to use it and change the NEXT_ACTION/PROJECT_STATUS cadence.

### R10. Session hygiene
- **What:**
  - Start a fresh session (`/clear`, then RESUME) at each phase or service boundary instead of one huge session. Resume is cheap by design (about 2–4k tokens injected), while a 150k-token context is re-sent on every turn.
  - Before an unavoidable long stretch, run `/compact focus on current step, files touched, open errors` instead of waiting for auto-compaction.

  On prompt caching: Claude Code caches the stable prefix automatically, and cache reads are billed at about 10% of input. The cache expires after about 5 minutes of inactivity **(verify the TTL for your plan)**, so a long idle pause after a big context makes the next turn pay full price. Editing CLAUDE.md or rule files mid-session invalidates the cached prefix **(verify)**, so do rule edits between sessions.
- **Saving:** M–L, growing with session length.
- **Risk:** Lost nuance across `/clear`. RESUME.md exists exactly for this.
- **Next step:** Add one line to CLAUDE.md: "One session per phase or per service; end each with RESUME.md written."

### R11. Skills and slash commands for repeated procedures
- **What:** Skills (`.claude/skills/<name>/SKILL.md`) put only their name and description in context until invoked **(verify)**. Candidates:
  - `checkpoint`: wraps R9
  - `build-test`: R4 usage and how to read failures
  - `new-service`: R6 generator plus the domain-code checklist
  - `deliver`: the packaging check from PRODUCT_RULES §5, the archive script and commit
  - `resume`: CHECKPOINT_PROTOCOL §8 table

  Moving the protocol details into skills lets CLAUDE.md stay tiny and avoids reading CHECKPOINT_PROTOCOL (79 lines) and PRODUCT_RULES (66 lines) at session start. They load only when needed.
- **Saving:** M (about 3–6k per session start, plus fewer "how do I…" re-derivations).
- **Risk:** A skill that doesn't trigger means a rule is missed. Mitigate with explicit `/name` calls in RESUME.md "Next" lines.
- **Next step:** Create `.claude/skills/{build-test,new-service,deliver}/SKILL.md`, each ≤ 40 lines.

### R12. Subagent policy
- **When subagents save tokens:**
  - Bounded, file-heavy work whose detail the main agent doesn't need afterwards, e.g. "implement the domain code of service X from the template + this spec, run `dbuild.sh`, report ≤ 10 lines"
  - Broad read-only searches
  - Parallel independent services *after* R6
- **When they cost tokens:**
  - Every subagent re-reads files and rules it needs (no shared context)
  - Unbriefed agents rebuild from scratch (attempt 1's 240k frontend)
  - Small tasks where the brief is as long as the work
- **Brief:** 20–40 lines. Give the goal, the paths to read (KNOWN_FACTS, template, spec section), what is done, the acceptance command, and the return format. Never paste file contents.
- **Model:** Define `.claude/agents/service-builder.md` and `frontend-builder.md` with `model: sonnet` and restricted tools. Keep the main orchestrator on the strongest model. Haiku is risky for JDK 27 / Spring Boot 4 / Jackson 3 code because those APIs are new and likely beyond its training. Use it only for mechanical tasks (renames, log trimming, formatting) **(assumption: verify quality on one service first)**.
- **Saving:** L if used for 8–10 templated services (it keeps the main context small). Negative if used without templates.
- **Next step:** Create `.claude/agents/service-builder.md` after the toolkit exists.

### R13. Incremental tests plus caches
- Run `:services:<x>:test` (or `--tests '*FooTest'`) while iterating. Run the full suite plus Testcontainers plus Playwright only at task or phase gates.
- Mount a named Docker volume for `/home/gradle/.gradle` and use `--build-cache`, so reruns are fast. This saves time; it saves tokens only through fewer retries and timeouts.
- Pre-pull the images once and record them in KNOWN_FACTS.
- **Saving:** M. **Risk:** A late integration break. The gates catch it. **Next step:** Bake both into `scripts/dbuild.sh` (R4).

### R14. Guard-rail hooks
- **What:** A `PreToolUse` hook on Bash that blocks (exit 2 with a message) a `gradle`/`docker build`/`npm test`/`playwright` command not run through `dbuild.sh` or not redirected to a file. It also blocks `cat` of files over 500 lines. The message tells the agent the cheap alternative. Implement it as an extra mode of the existing `checkpoint_hook.py`.
- I'm not aware of a supported way for a PostToolUse hook to rewrite or shorten the output of built-in tools. It can only add context (MCP tool output can be replaced) **(verify)**. So prevent large output; don't trim it afterwards.
- **Saving:** M (enforces R4/R7 automatically). **Effort:** M. **Risk:** False positives that block legitimate commands. Allow an escape token such as `# allow-verbose`.
- **Next step:** Add a `PreToolUse` entry in `.claude/settings.json` plus a `guard` mode in the hook.

### R15. Workflow / multi-agent fan-out
- Parallel multi-agent runs multiply cost: each agent carries its own context, and total tokens are roughly the sum of all of them. They buy wall-clock time, not tokens.
- They pay off only for genuinely independent units with a shared template and facts file, such as building 6 services from the generator in parallel, each verified by `dbuild.sh`.
- Do not use them for design, for anything touching shared files (`settings.gradle.kts`, compose, version catalog), or before the stack is frozen.
- **Assumption to verify:** the exact cost and limits of the Workflow tool in your Claude Code version.
- **Next step:** None now. Reconsider after R6 is proven on one service.

## 4. Rule-file reading: start versus on demand
| File | Lines | Read at session start? | Recommendation |
|---|---|---|---|
| `CLAUDE.md` | 24 | Always (auto) | Keep ≤ 40. Add R2/R7/R10 lines. Do not `@import` other files (imports load fully every session) **(verify)** |
| `RESUME.md` | ≤ 40 | Injected by hook | Keep. It is the main anchor |
| `MASTER_RULES.md` | 28 | First use only | Fine |
| `PRODUCT_RULES.md` | 66 | First use only | Fine. The §3 stack table could move to KNOWN_FACTS |
| `CHECKPOINT_PROTOCOL.md` | 79 | Only on disagreement | Move §2–5 into the `checkpoint` skill |
| `MASTER_PROMPT.md` | 476 | Never by default | Keep as the authority. Never read in full on resume (the CLAUDE.md in the system context still says "read on first use", which the on-disk CLAUDE.md has already relaxed) |
| `*_RULES.md` (7 small files) | 5–10 each | On demand | Merge into one `instructions/ENGINEERING_RULES.md` (about 50 lines): one read instead of 7 |
| `input/inbox/esmp_sample_dump.sql` | 1,294 | Never in full | Use `grep` for tables and `head` for samples |

## 5. Communication
- Ask once, upfront (R1). Group any later questions in one message, as the master prompt §7 already says.
- Progress messages: one line per step ("T-004.3 DONE: order-service CRUD, 14 tests green"). The session report uses the 5 MASTER_RULES headings, ≤ 2 lines each.
- Don't restate requirements or plans in chat. Point to the file instead.

## 6. Adopt first (top 5)
1. **R1:** Phase-1 gate questionnaire (stack, MVP cut, disk, docs, WIP commits). No code before `DEC-stack` is approved. Edit `instructions/PRODUCT_RULES.md` §5.
2. **R2:** Standing approval for WIP commits to `wip/<product>` after every DONE step. Add a line to `CLAUDE.md`.
3. **R3:** Create `toolkit/KNOWN_FACTS.md` with all verified versions, images, API names and Docker fixes, and read it before any research.
4. **R4 + R5:** `scripts/dbuild.sh` (quiet Docker Gradle, log to file, summary only) plus an `env.BASH_MAX_OUTPUT_LENGTH` cap in `.claude/settings.json`.
5. **R6:** `toolkit/` with Gradle convention plugins, common-lib and a service template, plus `scripts/new-service.sh`. Bootstrap them from the first service of the next run, then generate the rest.
