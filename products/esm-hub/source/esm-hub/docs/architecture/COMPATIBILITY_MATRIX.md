# esm-hub Compatibility Matrix

Source of truth for versions: `gradle/libs.versions.toml`, the Spring Boot BOM, `docker-compose.yml`, `infrastructure/docker/service.Dockerfile`, `frontend/package.json` and `.github/workflows/ci.yml`. Versions were checked on 2026-11-19 (execution decision D-003) and verified by the JDK 27 build spike. Re-check support dates at each release (§20).

| Technology | Selected version | Runtime it needs | Dependency compatibility | Database compatibility | Build / deploy requirements | Support lifecycle | Known limitations |
|---|---|---|---|---|---|---|---|
| OpenJDK (Temurin) | 27 (27.0.1) | — | Supported by Spring Boot 4.1 and Gradle 9.9 (proven by the spike) | — | Image `gradle:9.9.1-jdk27` (build), `eclipse-temurin:27-jre` (run) | **Non-LTS**: superseded by JDK 28 (Mar 2027), then unsupported | Move to JDK 25 LTS before production (TECH_STACK §3) |
| Gradle | 9.9.1 (wrapper) | JDK 17+ to run; toolchain 27 | Spring Boot Gradle plugin 4.1.2 | — | `./gradlew` or `scripts/build.sh` (runs in Docker) | Current major | Dependency locking not yet enabled |
| Spring Boot | 4.1.2 | JDK 17+ (tested on 27) | Spring Framework 7, Hibernate 7, Jackson 3, Micrometer, Testcontainers 2 (all through the BOM) | PostgreSQL JDBC driver from the BOM | Fat jar `app.jar` per service | OSS support per the Spring policy (about 13 months per minor) | Boot 4 removed some 3.x starters; use the new `*-webmvc` starter names |
| Spring Cloud | 2025.1.4 | Boot 4.1.x | Release train matched to Boot 4.1 | — | Gateway only | Matches the Boot 4.1 line | Gateway is WebMVC-based (not reactive) |
| springdoc-openapi | 3.2.0 | Boot 4.x | Boot 4 line | — | `/v3/api-docs` per service | Active | — |
| Hibernate ORM / Spring Data JPA | Through the BOM (7.x) | JDK 17+ | Boot 4.1 | PostgreSQL dialect | — | Active | — |
| Flyway | Through the BOM + `flyway-database-postgresql` | JDK 17+ | Boot 4.1 | PostgreSQL 16 (supported) | Migrations in `db/migration`, seed in `db/seed` | Active (Community) | Released migrations are never edited |
| PostgreSQL | 16 (`postgres:16-alpine`) | — | JDBC driver from the BOM | — | One DB per service (`infrastructure/postgres` init) | Community support to Nov 2028 | — |
| Apache Kafka | 4.4.0 (`apache/kafka:4.4.0`, KRaft) | JDK 17+ (in the image) | spring-kafka from the BOM; Testcontainers Kafka | — | Single broker in Compose | Active | Single broker = no HA locally. Production needs 3 brokers |
| Testcontainers | 2.0.5 (BOM) | Docker | JUnit 5 Jupiter | PostgreSQL 16, Kafka 4.4 images | Needs a Docker socket in the build container | Active | IT tests are slower (about 1 min per service) |
| JUnit 5 / Mockito | Through the BOM | JDK 17+ | Boot 4.1 test starter | — | — | Active | — |
| React | 19.3 | Node 24 (build only) | Vite, TypeScript | — | nginx static image (`web`) | Active | — |
| Node.js | 24 LTS (CI) | — | npm lockfile | — | Build only | LTS to Apr 2028 | — |
| Playwright | 1.65 | Node 24 | — | — | Runs against the composed stack | Active | Browsers come from the Playwright image |
| Mailpit | v1.27 | — | SMTP | — | Local/demo only | Active | Not for production |
| Trivy action | 0.33.1 | GitHub Actions | — | — | CI scan of dependencies and images | Active | — |
| Docker / Compose | Engine 24+, Compose v2 | — | — | — | `docker compose up` | — | About 10 JVMs: allow at least 8 GB RAM |
