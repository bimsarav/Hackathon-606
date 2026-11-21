# Product Delivery Rules

Source: user instruction, 2026-11-19 (rules update after the first challenge). These rules are **user instructions**, so they rank above the master prompt and every other rule file.
Where they conflict with the master prompt (folder structure, "avoid microservices"), **these rules win**.

## 1. What is delivered
- Each requirement placed in `input/` becomes a **product** delivered to the client.
- Pick a fitting product name from the requirement: short, descriptive, kebab-case (e.g. `service-hub`). Record it and the rationale in `execution/DECISIONS.md` before creating folders.
- When all changes and testing are finished, the **entire solution for that requirement lives in the product folder**. Nothing product-specific (code, tests, infrastructure, product docs) stays elsewhere in the workspace. Only `input/`, `instructions/`, `execution/`, `toolkit/`, `scripts/` and `CLAUDE.md` stay at the project root; they are the AI working files and are never part of the delivery. Products receive a *copy* of a `toolkit/stacks/<profile>/` skeleton through `scripts/new-product.sh` (user instruction 2026-11-20).

## 2. Folder layout (approved by the user 2026-11-19)
```
products/
└── <product-name>/                     product delivery folder
    ├── CONFLUENCE_PAGE.md              Confluence-ready page (see §6)
    └── source/
        └── <product-name>/             the code base: a git-ready repository
            ├── README.md               overview, prerequisites, build, run, test, deploy, push-to-git steps
            ├── .gitignore  .gitattributes  .editorconfig  .env.example
            ├── docker-compose.yml      full stack locally with one command
            ├── services/               one folder per Spring Boot microservice (+ api-gateway)
            ├── frontend/               React application
            ├── e2e/                    Playwright tests
            ├── infrastructure/         Dockerfiles not kept in modules, reverse proxy, k8s/Helm if produced
            ├── scripts/                build, deploy, rollback, backup, restore
            ├── docs/                   architecture, ADRs, API specs, data model, security, testing, runbooks, delivery report
            └── .github/workflows/      CI pipeline
```
- The repository must be **ready to push**: no secrets, no build output, no IDE files, no AI tracking files, no absolute paths, no references to the workspace outside it. Its README holds the exact `git init / git remote add / git push` steps.
- Do not run `git init` inside the workspace: it would create a nested repo in this project's git. The client initialises it, or the user asks for it explicitly.
- The repository must build, test and run **without AI involvement**: plain Docker, Gradle wrapper and npm commands, all documented in its README.

## 3. Technology stack (mandatory for esm-hub; new products: see below)
> **Update (user instruction 2026-11-20):** `instructions/TECH_STACK_STANDARDS.md` governs every **new** product: run its §9.16 selection workflow (full text MASTER_PROMPT §9): present the numbered stack menu with "Let the AI Agent Decide" as the last option, and wait for the user's choice unless told to proceed autonomously. Options come from the verified stack profiles in `toolkit/stacks/` where they fit (MASTER_PROMPT §9.16.0: freshness check → menu → `scripts/new-product.sh`) for that product's domain, and record the result in the product's ADRs. The "always microservices + Kafka" rule below then no longer applies by default; the table is a starting point only. **esm-hub keeps this table** and must still carry the §9.16 documents (`docs/architecture/TECH_STACK.md`, `TECHNOLOGY_COMPARISON.md`, `COMPATIBILITY_MATRIX.md`, ADRs in `docs/architecture/adr/`).

| Concern | Technology |
|---|---|
| Language/runtime | **OpenJDK, latest stable GA release**. Check the actual latest GA at build start and record the version in DECISIONS.md. If a required framework does not support it yet, use the newest version it supports, and record why |
| Build | **Gradle** (wrapper, Kotlin DSL, version catalog). User instruction 2026-11-19 |
| Backend | **Spring Boot microservices** (always microservices, the user's decision). Split by business domain; Spring Cloud Gateway as the single entry point; one database or schema per service (database-per-service) |
| Messaging | **Apache Kafka** for asynchronous, event-driven communication between services where it fits (domain events, notifications, audit, integration). Synchronous REST only where a request/response is needed |
| Frontend | **React** (current stable, TypeScript, Vite) |
| Backend tests | **JUnit 5 + Mockito** (unit). Add Spring Boot test slices and **Testcontainers** (PostgreSQL, Kafka) for integration |
| Frontend tests | **Playwright** end-to-end (plus component/unit tests with the React tooling where useful) |
| Packaging/runtime | **Docker**: a multi-stage Dockerfile per service and for the frontend; `docker-compose.yml` for the full stack |
| Other | Use every technology that genuinely serves the requirement: PostgreSQL, Flyway, OpenAPI (springdoc), Spring Security (OAuth2/JWT), Actuator + Micrometer/Prometheus, centralised config, resilience (Resilience4j), nginx, CI. Justify each in an ADR |

## 4. Build and verification
- No toolchain on the host is assumed. Build and test inside Docker images (Gradle + JDK, Node), so the client can reproduce every result.
- "Done" means: every module builds, all JUnit/Mockito/Testcontainers tests pass, Playwright passes against the composed stack, the dependency vulnerability scan is clean or each finding is documented, and `docker compose up` brings up a healthy stack. Record the commands and results in the product's `docs/testing/test-report.md` and in `execution/logs/execution.log`.

## 5. Working method
- Phases, checkpoints and logging follow MASTER_RULES and CHECKPOINT_PROTOCOL unchanged. The tracking files stay in `execution/`.
- Work directly in `products/<product-name>/source/<product-name>/`. Before delivery, run a **packaging check**:
  1. Nothing product-related is left outside the product folder.
  2. A clean clone-style build from an empty Docker state succeeds.
  3. A secret and junk scan finds nothing.
  4. The README steps work exactly as written.
- Delivery finishes with the log lifecycle step (CHECKPOINT_PROTOCOL §9): commit the product, then run `scripts/archive-product-logs.sh <product-name> --status delivered --yes` and commit the reset, so the next product starts with empty logs. Archives stay local (git-ignored); logs of unfinished work are always committed.
- Input files in `input/` are never modified. A copy of any seed or sample data the product needs goes inside the repository.

## 6. Confluence page (`products/<product-name>/CONFLUENCE_PAGE.md`)
Content that can be pasted straight into a Confluence page (the Markdown paste or Markdown macro), so:
- Self-contained: **no relative links** to repo files and no local images. Point to the git repo by URL placeholder `<repository-url>` instead.
- Only Markdown that Confluence renders reliably: headings, paragraphs, bullet and numbered lists, simple pipe tables (no merged cells, no line breaks inside cells), fenced code blocks, bold/italic, horizontal rules.
- **No Mermaid or HTML.** Diagrams as plain-text (ASCII) diagrams inside code blocks.
- Use plain text labels (Done, Partial, Not done) instead of emoji status symbols.
- Suggested sections: Overview · Business problem and goals · Scope and features · Architecture (services, Kafka topics, data stores) · Technology stack · Environments and deployment · How to build, run and test · API summary · Security · Test results · Known limitations and open decisions · Roadmap · Contacts/ownership (placeholders).

## 7. No build-process traces in client deliverables (user instruction 2026-11-21)
The product solution and its Confluence pages are shared with the client. They must never mention how the product was built with the AI assistant: no "approved by the user", "(user 2026-11-21)", "user decision / request / instruction"; no task or decision IDs (T-511, D-028); no `execution/` paths or log files; no MASTER_PROMPT or engineering-standards section numbers; no stack-profile, toolkit or technology-selection-checkpoint notes; no "teammate" or session remarks. Provenance stays in `execution/` only.

**Do not write traces in the first place.** New docs, ADRs, code comments, tests and commit-ready files state neutral facts ("Accepted (2026-11-21)", "Scope: G9 only", "skipped by decision", "product-owner decision Q8").

**Cleaning existing traces:**
1. Change only files inside `products/<product-name>/source/<product-name>/`; nothing outside that path.
2. Change documentation only (`README.md`, `docs/**/*.md`). Never change system code while cleaning: no edits under `backend/`, `frontend/`, `e2e/`, `scripts/`, `compose.yml` or other code and config files, comments included. Docs that must stay identical to a file under the code tree (e.g. `docs/testing/*-selection.md` and `backend/app/data/model_docs/`) stay unchanged; list them as remaining.
3. Where a removed text pointed somewhere (a log, an approval, an evidence file), say where the reader finds it inside the source instead (e.g. `docs/testing/test-report.md`, `docs/delivery/MVP_AND_INCREMENTAL_PLAN.md`).
   References to design records (ADRs, cards, reports) show their path inside the source in visible text, not only as a link target, e.g. "[ADR 0011](docs/architecture/adr/0011-….md) (`docs/architecture/adr/0011-….md`)".
4. Prove functionality is unchanged: `git diff --name-only` shows only `.md` files, and `scripts/check.sh` passes. Save its output under `execution/logs/output/`.
5. Report every trace left in code or locked docs, and ask before touching them.
