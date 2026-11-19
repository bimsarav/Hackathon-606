# hack-isa: resumable autonomous engineering project

This project runs under the user's master prompt, saved word for word in `instructions/MASTER_PROMPT.md`.
Progress lives ONLY in files. Never rely on conversation history or memory.

## On every session start, or when the user says RESUME, STATUS or anything else
1. Read `instructions/MASTER_RULES.md` (summary), `instructions/PRODUCT_RULES.md` and `instructions/CHECKPOINT_PROTOCOL.md`.
   Read `instructions/MASTER_PROMPT.md` in full on first use in a session, or whenever a rule is unclear.
2. Read `execution/PROJECT_STATUS.md`, `execution/CURRENT_TASK.md` and `execution/NEXT_ACTION.md`.
3. Read the last 20 lines of `execution/logs/execution.log` and `execution/logs/errors.log`.
4. Recover the position using the rules in `CHECKPOINT_PROTOCOL.md`.
5. Tell the user in 3–5 lines: the last completed step, any interrupted step and its verified state, and what runs next. Then continue.
   For STATUS: report only, don't continue.

Do not redo steps marked `[x]` unless the files contradict them.

## Delivery rules (user instruction 2026-11-19, they override the master prompt where they differ)
- Every requirement becomes a named product: `products/<product-name>/` holds `CONFLUENCE_PAGE.md`, and `source/<product-name>/` is the git-ready code base.
- Stack: latest stable OpenJDK · Spring Boot microservices · Kafka where it fits · React · JUnit 5 + Mockito (+ Testcontainers) · Playwright · Docker.
- At delivery, the whole solution is inside the product folder and builds, tests and deploys without AI. Details: `instructions/PRODUCT_RULES.md`.
