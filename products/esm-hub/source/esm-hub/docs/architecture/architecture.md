# esm-hub Architecture and Engineering Conventions

esm-hub is an Enterprise Service Management platform for Northstar Holdings (Abu Dhabi, Dubai, London, Colombo), built as Spring Boot microservices with Kafka, a React frontend and PostgreSQL. This document is binding for every module.

## 1. System view
```
                    Browser (React SPA)
                           |
                   +-------v--------+   serves the SPA, proxies /api/* to the gateway, TLS in production
                   |  web (nginx)   |
                   +-------+--------+
                           |
                   +-------v--------+   Spring Cloud Gateway: routing, request id, login rate limit
                   |    gateway     |
                   +-------+--------+
     +--------+--------+---+----+--------+---------+-----------+-----------+----------+
     |        |        |        |        |         |           |           |          |
 directory incident request  change    asset   knowledge  notification  reporting   audit
 -service  -service -service -service -service -service    -service     -service   -service
     |        |        |        |        |         |           |           |          |
     +--------+--------+--------+--------+---------+-----------+-----------+----------+
                           |                                   |
                PostgreSQL 16 (one database per service)   Apache Kafka 4.4 (KRaft)
```
Mailpit (local SMTP sink with web UI) receives email in the local and demo stacks.

## 2. Services (bounded contexts)
| Service | Port | Owns (database `esm_<name>`) | Responsibilities |
|---|---|---|---|
| gateway | 8080 | none | Routes `/api/v1/**`, request id, login rate limit |
| directory-service | 8081 | companies, offices, departments, users, roles, teams, service categories, services | Login, RS256 JWT + JWKS, users/roles/teams admin, org hierarchy, service master data; publishes directory state topics |
| incident-service | 8082 | incidents, comments, worklogs, incident events, priorities, statuses, transitions, SLA policies, calendars, holidays, escalation and assignment rules, problems, problem links | Incident lifecycle, business-hours SLA engine, escalation scheduler, auto-close, problem management |
| request-service | 8083 | catalogue items, approval steps, service requests, request approvals | Catalogue, requests, sequential cost-conditional approvals, fulfilment |
| change-service | 8084 | change requests, change approvals | Change lifecycle, risk/impact assessment, approval policy, collision calendar |
| asset-service | 8085 | assets, asset assignments | Inventory, lifecycle, assignment history, warranty |
| knowledge-service | 8086 | articles, article feedback | KB workflow (four-eyes publish), full-text search, feedback |
| notification-service | 8087 | notifications | Consumes domain events, notification rules, in-app inbox, email (SMTP) with retry/backoff/dead-letter |
| audit-service | 8088 | audit_records (append-only) | Consumes `audit.events`, immutable store, query and CSV export |
| reporting-service | 8089 | read-model projections | Consumes state topics (CQRS), dashboards, reports, CSV export |

Frontend: `frontend/` (React 19 + TypeScript + Vite), served by nginx (`web`).

## 3. Communication
**Synchronous REST** (via the gateway) for all UI calls. Services do **not** call each other synchronously; data they need from another context arrives over Kafka and is kept as a local read replica.

| Topic | Kind | Key | Producer | Consumers |
|---|---|---|---|---|
| `directory.users`, `directory.teams`, `directory.services`, `directory.offices` | compacted state | id | directory | services needing directory data (via esm-directory-replica), reporting |
| `incident.incidents`, `incident.problems`, `request.requests`, `change.changes`, `asset.assets` | compacted state | id | owner | reporting |
| `incident.events`, `request.events`, `change.events`, `asset.events`, `knowledge.events` | domain events (7 days) | aggregate id | owner | notification |
| `audit.events` | domain events (30 days) | entity id | all services | audit |
| `<topic>.DLT` | dead letters | same | consumer error handler | ops |

**Envelope** (`com.esmhub.common.events.EventEnvelope`): `eventId, eventType, occurredAt, companyId, actorId, correlationId, aggregateType, aggregateId, version, payload`. State topics use event type `<aggregate>.snapshot` with the full state as payload; a null value is a tombstone.

**Reliability:**
- Transactional outbox (`OutboxPublisher` → `outbox_events` → `OutboxRelay`).
- Idempotent consumers (`EventReader.once`, using `processed_events`).
- Retries with exponential backoff, then a `.DLT` topic.
- Snapshot bootstrap (`SnapshotSource`, `snapshot_state`) republishes state topics on first start or after a seed.
- Correlation ID carried from `X-Request-ID` into the Kafka header `correlationId`.

## 4. Security
- directory-service issues **RS256 JWTs** (60 min). Claims: `sub`, `cid` (company), `roles`, `teams`, `name`, `email`. Keys come from env (`ESM_JWT_PRIVATE_KEY`/`ESM_JWT_PUBLIC_KEY`); in `local`/`test` a key is generated if unset.
- Every service is a Spring Security **resource server**. It validates against `${ESM_JWKS_URI:http://directory-service:8081/.well-known/jwks.json}`, and `roles` become `ROLE_<name>`. Deny by default. Always public: health, info, prometheus (blocked at the edge), OpenAPI docs, plus each service's `esm.security.public-paths`.
- **Tenant boundary = company.** Every query filters by `companyId`; records of another company return 404.
- Roles: EMPLOYEE, SERVICE_DESK_AGENT, TECHNICIAN, TEAM_LEAD, SERVICE_MANAGER, CHANGE_MANAGER, ASSET_MANAGER, KNOWLEDGE_EDITOR, ADMIN, AUDITOR. Every authenticated user has employee capabilities.
- Login: bcrypt, lockout after 5 failures for 15 min, gateway rate limit. Containers run non-root. Secrets come only from env. The audit store is append-only (DB trigger).

## 5. Code conventions
- **Java 27, Spring Boot 4.1, Gradle 9.9 (Kotlin DSL)**. The multi-project build includes `libs:*` and `services:*`. Versions are in `gradle/libs.versions.toml`. Convention plugins live in `buildSrc`:
  - `esm.java-library`: Java 27 toolchain, Boot BOM, JUnit, JaCoCo.
  - `esm.spring-service`: Boot plugin, esm-common, and an `integrationTest` suite in `src/integrationTest/java`, run by `check`.
- Packages `com.esmhub.<service>.<feature>`: Controller (DTO records) → Service (rules, `@Transactional`) → Repository (Spring Data JPA). Entities never leave the service layer. Constructor injection only.
- Errors are RFC 9457 problem+json via the common handler: `NotFoundException` 404, `ForbiddenException` 403, `ConflictException` 409, `BusinessRuleException` 422, validation 400. Every body carries `requestId`.
- REST is `/api/v1/<resource>`. Lists take `?page=1&size=25` (≤ 200) and return `PageResponse{items,total,page,size}`. CSV exports go through `CsvWriter` (formula-safe), are role-restricted and audited.
- Controllers take a `CurrentUser` parameter (from the JWT). Never take the actor from the body.
- Flyway: service migrations in `db/migration`. Common tables come from `classpath:db/common` and directory replicas from `classpath:db/directory`. The demo seed is in `db/seed`, enabled by profile `demo`.
- Jackson 3 (`tools.jackson.*`, inject `JsonMapper`). UTC `Instant`/`TIMESTAMPTZ`; money as `BigDecimal`/`NUMERIC(12,2)`; `BIGINT` identity IDs (legacy IDs preserved).
- Audit: `AuditPublisher.record(entityType, id, action, before, after)` for every sensitive change.
- Structured ECS logs with `requestId`/`userId` in the MDC; never log bodies or secrets. Actuator health/info/prometheus. springdoc OpenAPI; the contract test writes `docs/api/<service>.json`.

## 6. Testing
- **Unit** (`./gradlew test`): JUnit 5 + Mockito + AssertJ.
- **Integration** (`./gradlew integrationTest`): `@SpringBootTest` + Testcontainers (PostgreSQL 16, `apache/kafka:4.4.0`) via `EsmContainers`; JWTs from `TestJwt.bearer(...)` (TEST-ONLY key, trusted in the `test` profile). Every endpoint needs happy-path, RBAC and tenant-isolation tests; Kafka needs round-trip tests.
- **Contract:** OpenAPI snapshot per service. **Frontend:** Vitest; **Playwright** E2E in `e2e/` against the composed stack.

## 7. Build and run
- `scripts/build.sh build` runs `./gradlew build` inside `gradle:9.9.1-jdk27`, with the Docker socket shared for Testcontainers.
- `infrastructure/docker/service.Dockerfile` (`ARG SERVICE`) builds each service on `eclipse-temurin:27-jre`, non-root, with a HEALTHCHECK.
- `docker compose up -d` starts the full stack; profile `demo` adds the seeded Northstar data.

## 8. ADRs (`docs/architecture/adr/`)
| ADR | Decision |
|---|---|
| 0001 | Microservices per bounded context, database-per-service |
| 0002 | Self-issued RS256 JWT + JWKS; OIDC-ready |
| 0003 | Company = tenant boundary |
| 0004 | Async integration only (state topics + local replicas) |
| 0005 | Transactional outbox, idempotent consumers, DLT |
| 0006 | Business-hours SLA in incident-service, due dates stored |
| 0007 | CQRS reporting read model |
| 0008 | Legacy dump → per-service demo seed, IDs preserved |
| 0009 | Gradle (Kotlin DSL, version catalog, buildSrc conventions) |
