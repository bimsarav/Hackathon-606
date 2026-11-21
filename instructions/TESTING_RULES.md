# Testing Rules
- Backend unit tests: **JUnit 5 + Mockito** for every service class with business logic.
- Backend integration tests: Spring Boot test slices plus **Testcontainers** (PostgreSQL, Kafka), against real infrastructure, never H2 standing in for PostgreSQL.
- Contract: each service's OpenAPI spec is generated and checked in. Breaking changes fail CI. Event schemas are tested for producer/consumer compatibility.
- Frontend: **Playwright** E2E against the full docker-compose stack (main user journeys per role); component tests where useful.
- Coverage is reported (JaCoCo). Aim for ≥ 80% line coverage on service and domain code.
- A test passes only if it actually ran. Record commands and results in `docs/testing/test-report.md` and `execution/logs/execution.log`.
- Manual UI testing (MASTER_PROMPT §17, `instructions/QA_RULES.md`) is separate from and in addition to the automated tests above: the Manual QA Engineer tests the running application through its UI, keeps a traceability matrix and a regression suite, and reports bugs. Automated suites passing is not manual QA, and manual QA is not a substitute for automated tests.
