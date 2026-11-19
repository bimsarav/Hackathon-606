# Product Delivery Rules

Source: user instruction, 2026-11-19 (rules update after the first challenge). These rules are **user instructions**, so they rank above the master prompt and every other rule file.
Where they conflict with the master prompt (folder structure, "avoid microservices"), **these rules win**.

## 1. What is delivered
- Each requirement placed in `input/` becomes a **product** delivered to the client.
- Pick a fitting product name from the requirement: short, descriptive, kebab-case (e.g. `service-hub`). Record it and the rationale in `execution/DECISIONS.md` before creating folders.
- When all changes and testing are finished, the **entire solution for that requirement lives in the product folder**. Nothing product-specific (code, tests, infrastructure, product docs) stays elsewhere in the workspace. Only `input/`, `instructions/`, `execution/` and `CLAUDE.md` stay at the project root; they are the AI working files and are never part of the delivery.

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
- The repository must build, test and run **without AI involvement**: plain Docker, Maven/Gradle wrapper and npm commands, all documented in its README.

## 3. Technology stack (mandatory)
| Concern | Technology |
|---|---|
| Language/runtime | **OpenJDK, latest stable GA release**. Check the actual latest GA at build start and record the version in DECISIONS.md. If a required framework does not support it yet, use the newest version it supports, and record why |
| Backend | **Spring Boot microservices** (always microservices, the user's decision). Split by business domain; Spring Cloud Gateway as the single entry point; one database or schema per service (database-per-service) |
| Messaging | **Apache Kafka** for asynchronous, event-driven communication between services where it fits (domain events, notifications, audit, integration). Synchronous REST only where a request/response is needed |
| Frontend | **React** (current stable, TypeScript, Vite) |
| Backend tests | **JUnit 5 + Mockito** (unit). Add Spring Boot test slices and **Testcontainers** (PostgreSQL, Kafka) for integration |
| Frontend tests | **Playwright** end-to-end (plus component/unit tests with the React tooling where useful) |
| Packaging/runtime | **Docker**: a multi-stage Dockerfile per service and for the frontend; `docker-compose.yml` for the full stack |
| Other | Use every technology that genuinely serves the requirement: PostgreSQL, Flyway, OpenAPI (springdoc), Spring Security (OAuth2/JWT), Actuator + Micrometer/Prometheus, centralised config, resilience (Resilience4j), nginx, CI. Justify each in an ADR |

## 4. Build and verification
- No toolchain on the host is assumed. Build and test inside Docker images (Maven/Gradle + JDK, Node), so the client can reproduce every result.
- "Done" means: every module builds, all JUnit/Mockito/Testcontainers tests pass, Playwright passes against the composed stack, the dependency vulnerability scan is clean or each finding is documented, and `docker compose up` brings up a healthy stack. Record the commands and results in the product's `docs/testing/test-report.md` and in `execution/logs/execution.log`.

## 5. Working method
- Phases, checkpoints and logging follow MASTER_RULES and CHECKPOINT_PROTOCOL unchanged. The tracking files stay in `execution/`.
- Work directly in `products/<product-name>/source/<product-name>/`. Before delivery, run a **packaging check**:
  1. Nothing product-related is left outside the product folder.
  2. A clean clone-style build from an empty Docker state succeeds.
  3. A secret and junk scan finds nothing.
  4. The README steps work exactly as written.
- Input files in `input/` are never modified. A copy of any seed or sample data the product needs goes inside the repository.

## 6. Confluence page (`products/<product-name>/CONFLUENCE_PAGE.md`)
Content that can be pasted straight into a Confluence page (the Markdown paste or Markdown macro), so:
- Self-contained: **no relative links** to repo files and no local images. Point to the git repo by URL placeholder `<repository-url>` instead.
- Only Markdown that Confluence renders reliably: headings, paragraphs, bullet and numbered lists, simple pipe tables (no merged cells, no line breaks inside cells), fenced code blocks, bold/italic, horizontal rules.
- **No Mermaid or HTML.** Diagrams as plain-text (ASCII) diagrams inside code blocks.
- Use plain text labels (Done, Partial, Not done) instead of emoji status symbols.
- Suggested sections: Overview · Business problem and goals · Scope and features · Architecture (services, Kafka topics, data stores) · Technology stack · Environments and deployment · How to build, run and test · API summary · Security · Test results · Known limitations and open decisions · Roadmap · Contacts/ownership (placeholders).
