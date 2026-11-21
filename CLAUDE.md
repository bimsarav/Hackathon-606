# hack-isa: resumable autonomous engineering project

This project runs under the user's master prompt, saved in `instructions/MASTER_PROMPT.md` (verbatim 2026-11-19; extended 2026-11-20 with §9 Technology Stack & Engineering Standards at the user's request).
Progress lives ONLY in files. Never rely on conversation history or memory.

## On every session start, or when the user says RESUME, STATUS or anything else
Cheapest path first (details: `instructions/CHECKPOINT_PROTOCOL.md` §8):
1. The SessionStart hook injects `execution/RESUME.md` plus the latest tool activity and session markers. If they are missing, read `execution/RESUME.md` yourself.
2. If the snapshot and the last activity agree, check only the files of the in-progress step (and any saved long-command output) and continue.
3. Only if they disagree, or on first use in a session: read `instructions/MASTER_RULES.md`, `instructions/PRODUCT_RULES.md`, `instructions/CHECKPOINT_PROTOCOL.md`, `execution/CURRENT_TASK.md` and the last 20 lines of `execution/logs/execution.log` and `errors.log`, `execution/qa/<product>/DEFECTS.md` and the last rows of `execution/judge/QUALITY_TRACKER.md`, then reconcile. Read `instructions/MASTER_PROMPT.md` only when a rule is unclear.
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
- Tech stack standards (user instruction 2026-11-20): `instructions/TECH_STACK_STANDARDS.md`. They apply to new products; esm-hub keeps the stack above and adds the §9.16 documents (TECH_STACK, TECHNOLOGY_COMPARISON, COMPATIBILITY_MATRIX).
- Stack profiles (user instruction 2026-11-20): new products pick from `toolkit/stacks/` (README + PROFILE.md only), run `scripts/check-stack-freshness.sh <profile>`, then `scripts/new-product.sh <profile> <name>`. Read `toolkit/KNOWN_FACTS.md` before researching. `toolkit/` and `scripts/` are never delivered.
- At delivery, the whole solution is inside the product folder and builds, tests and deploys without AI. Details: `instructions/PRODUCT_RULES.md`.
- Product vs AI Agent stack (user 2026-11-20, MASTER_PROMPT §9.24): the numbered menu picks only the product stack; the agent's own stack is recorded in `instructions/AGENT_TECH_STACK.md`; new products also keep `docs/architecture/ENGINEERING_STANDARDS.md`.
- Airline domain research (user 2026-11-20, MASTER_PROMPT §15): standing research role; knowledge goes to `documentation/knowledge-base/airline/` with sourced, labelled claims. Summary: `instructions/DOMAIN_RESEARCH_RULES.md`.
- Delivery cadence (user 2026-11-20, overrides the one-shot delivery flow): (1) prepare design diagrams first and tell the user where to view them; (2) define an MVP and build it first; (3) host the finished MVP and tell the user how to view it; (4) keep an incremental deployment plan (phases after the MVP) in the product's docs; each later phase starts only with the user's explicit approval. Record the phase gates in execution/DEPLOYMENT_STATUS.md.
- Parquet (user 2026-11-20, MASTER_PROMPT §9.25): convert tabular CSV/JSON to Parquet first and work on that (column + filter pushdown, DuckDB/Polars, explicit types, sensible partitions and file sizes).
- Cloud deployment (user instruction 2026-11-20, MASTER_PROMPT §13): a product is COMPLETED only when it is deployed, running and verified in the cloud environment the user provides, and the user has the URL. Never assume a provider or invent results; without access, the status is BLOCKED / DEPLOYMENT PENDING. State: `execution/DEPLOYMENT_STATUS.md` (read on resume). Summary: `instructions/DEPLOYMENT_RULES.md`.
- Cloud details (user 2026-11-20) arrive in a separate folder in `input/`, possibly mid-build: check `input/` for them at every resume and step change; before deployment, ask the user again for anything still missing.
- Server operations & restart resilience (user 2026-11-20, MASTER_PROMPT §14): deployment also needs the server baseline, auto-start + health checks + log rotation, backups, monitoring and a recorded reboot test; until verified, report `DEPLOYED – OPERATIONAL VERIFICATION PENDING`, never production-ready.
- Manual QA Engineer (user 2026-11-22, MASTER_PROMPT §17): every delivered feature is tested through the running UI against the requirements and delivery reports (functional, usability, regression, negative, end-to-end, per role) in a separate agent context; bugs are reported (QA-<code>-<nnn>) and retested before closure; each cycle ends with a QA verdict, before the Judge. After bug fixes QA tests only the fixed bugs and related areas; after a new feature, a QA phase on the feature and related areas; new bugs from the changes are fixed and retested in repeated cycles until clean; every implementation and QA cycle is shown to the user as a short block, with a summary at the end (QA_RULES §5). Rules: `instructions/QA_RULES.md`. Working material in `execution/qa/<product>/` (read `DEFECTS.md` on resume); client-facing QA docs in the product's `docs/testing/manual-qa/`.
- AI Judge (user 2026-11-21, MASTER_PROMPT §16): independent evaluation of every significant deliverable in a separate agent context, scored out of 100 against the product's own criteria (`execution/judge/<product>/CRITERIA.md`); critical findings block approval; every completed process ends with its Judge score. Rules: `instructions/JUDGE_RULES.md`. Judge material stays in `execution/judge/`, never in deliverables.
