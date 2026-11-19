# Testing Rules
- Backend unit tests: **JUnit 5 + Mockito** for every service class with business logic.
- Backend integration tests: Spring Boot test slices plus **Testcontainers** (PostgreSQL, Kafka), against real infrastructure, never H2 standing in for PostgreSQL.
- Contract: each service's OpenAPI spec is generated and checked in. Breaking changes fail CI. Event schemas are tested for producer/consumer compatibility.
- Frontend: **Playwright** E2E against the full docker-compose stack (main user journeys per role); component tests where useful.
- Coverage is reported (JaCoCo). Aim for ≥ 80% line coverage on service and domain code.
- A test passes only if it actually ran. Record commands and results in `docs/testing/test-report.md` and `execution/logs/execution.log`.
