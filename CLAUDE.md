# hack-isa: resumable autonomous engineering project

This project runs under the user's master prompt, saved word for word in `instructions/MASTER_PROMPT.md`.
Progress lives ONLY in files. Never rely on conversation history or memory.

## On every session start, or when the user says RESUME, STATUS or anything else
Cheapest path first (details: `instructions/CHECKPOINT_PROTOCOL.md` §8):
1. The SessionStart hook injects `execution/RESUME.md` plus the latest tool activity and session markers. If they are missing, read `execution/RESUME.md` yourself.
2. If the snapshot and the last activity agree, check only the files of the in-progress step (and any saved long-command output) and continue.
3. Only if they disagree, or on first use in a session: read `instructions/MASTER_RULES.md`, `instructions/PRODUCT_RULES.md`, `instructions/CHECKPOINT_PROTOCOL.md`, `execution/CURRENT_TASK.md` and the last 20 lines of `execution/logs/execution.log` and `errors.log`, then reconcile. Read `instructions/MASTER_PROMPT.md` only when a rule is unclear.
4. Tell the user in 3–5 lines: the last completed step, any interrupted step and its verified state, and what runs next. Then continue.
   For STATUS: report only, don't continue.

## While working (mandatory)
- Rewrite `execution/RESUME.md` (≤ 40 lines) at every step change; log STARTED/PROGRESS/DONE in `execution/logs/execution.log`; keep file manifests for multi-file steps.
- Save the output of long commands under `execution/logs/output/` and note them in RESUME.md; never re-run a long build without checking its saved output first.
- Logs of unfinished work are committed. At product delivery (or drop), run `scripts/archive-product-logs.sh <product-name> --status delivered|dropped --yes`: logs move to the git-ignored `execution/archive/`, and the next product starts with empty logs (CHECKPOINT_PROTOCOL §9).

Do not redo steps marked `[x]` unless the files contradict them.

## Delivery rules (user instruction 2026-11-19, they override the master prompt where they differ)
- Every requirement becomes a named product: `products/<product-name>/` holds `CONFLUENCE_PAGE.md`, and `source/<product-name>/` is the git-ready code base.
- Stack: latest stable OpenJDK · Spring Boot microservices · Kafka where it fits · React · JUnit 5 + Mockito (+ Testcontainers) · Playwright · Docker.
- At delivery, the whole solution is inside the product folder and builds, tests and deploys without AI. Details: `instructions/PRODUCT_RULES.md`.
