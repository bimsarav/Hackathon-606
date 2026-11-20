# Technical Rules
Mandatory stack: see `PRODUCT_RULES.md` §3 (esm-hub). New products: `TECH_STACK_STANDARDS.md` (user instruction 2026-11-20); the lines below then apply only where that product chose these technologies.
- Java: latest stable GA OpenJDK (verify the version at build start). Spring Boot (current GA) with Spring Cloud (Gateway, config) where needed.
- Build: **Gradle** (user instruction 2026-11-19) with the Gradle wrapper (`./gradlew`), Kotlin DSL (`*.gradle.kts`), multi-project build (`settings.gradle.kts`), a version catalog (`gradle/libs.versions.toml`) and the Spring Boot BOM via `platform(...)`; shared conventions in `buildSrc` convention plugins; exact versions pinned.
- Persistence: PostgreSQL, one database or schema per service; schema changes only through Flyway migrations (`V<n>__<desc>.sql`), never edited once released.
- Messaging: Kafka topics named `<domain>.<entity>.<event>` (e.g. `incident.ticket.created`), versioned JSON (or Avro) event schemas, idempotent consumers, a transactional outbox for publish-after-commit, dead-letter topics.
- APIs: REST, OpenAPI 3 via springdoc, versioned under `/api/v1`, problem+json (RFC 9457) errors.
- Frontend: React + TypeScript + Vite; API types generated from or checked against the OpenAPI specs.
- Configuration through environment variables and Spring profiles only; `.env` is never committed.
- Timestamps in UTC (`Instant`/`TIMESTAMPTZ`); convert to local time only at the edges.
