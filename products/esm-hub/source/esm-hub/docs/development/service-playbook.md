# Service Implementation Playbook

How to build an esm-hub microservice. Read `docs/architecture/architecture.md` first; it is binding. The **reference implementation is `services/directory-service`**: copy its structure, configuration and test style.

## 1. Files to create for `services/<name>`
```
services/<name>/build.gradle.kts            plugins { id("esm.spring-service") }  (+ dependencies, e.g. implementation(project(":libs:esm-directory-replica")))
src/main/java/com/esmhub/<short>/service/<Short>ServiceApplication.java   @SpringBootApplication @ConfigurationPropertiesScan
src/main/java/com/esmhub/<short>/service/<feature>/...                  Entity, Repository (top-level interfaces!), Dtos (records), Service, Controller
src/main/java/com/esmhub/<short>/service/events/...                     Topics bean (KafkaAdmin.NewTopics), SnapshotSource, event publishing, listeners
src/main/resources/application.yml                                      copy directory-service's file; change port, name, DB, flyway locations
src/main/resources/db/migration/V1__init.sql                            own schema; NEVER other services' tables
src/main/resources/db/seed/V900__demo_seed.sql                          GENERATED via tools/seed (see §5)
src/test/java/...                                                       JUnit 5 + Mockito unit tests (*Test)
src/integrationTest/java/...                                            @SpringBootTest + EsmContainers + TestJwt (*IT)
src/integrationTest/resources/application-test.yml                      see §3
```
The module is already included in `settings.gradle.kts`. Do not edit the settings, `buildSrc`, `gradle/libs.versions.toml` or `libs/*` without coordinating; ask in your final report instead. Adding a catalog entry is acceptable if it is strictly needed.

## 2. application.yml essentials
- `server.port` from the architecture table. `spring.application.name: <name>`. Datasource `${ESM_DB_URL:jdbc:postgresql://localhost:5432/esm_<short>}` with `${ESM_DB_USER:esm}` / `${ESM_DB_PASSWORD:esm}`.
- `spring.jpa.hibernate.ddl-auto: validate`, `open-in-view: false`.
- `spring.flyway.locations: classpath:db/common,classpath:db/migration` (add `classpath:db/directory` when using esm-directory-replica). The `demo` profile document appends `classpath:db/seed`.
- Kafka: `spring.kafka.bootstrap-servers: ${ESM_KAFKA:localhost:9092}`; producer `acks: all`, `enable.idempotence: true`.
- Resource server: `spring.security.oauth2.resourceserver.jwt.jwk-set-uri: ${ESM_JWKS_URI:http://localhost:8081/.well-known/jwks.json}`.
- `management.endpoints.web.exposure.include: health,info,prometheus`, `management.endpoint.health.probes.enabled: true`, `logging.structured.format.console: ${ESM_LOG_FORMAT:}`.

## 3. application-test.yml (src/integrationTest/resources)
```yaml
spring.security.oauth2.resourceserver.jwt.public-key-location: classpath:test-jwt/public.pem
esm.outbox: { poll-ms: 200, initial-delay-ms: 200 }
```
The `test` profile is activated by the build. Testcontainers come from `@Import(EsmContainers.class)`. Mint tokens with `TestJwt.bearer(userId, companyId, List.of(teamIds), "ROLE_NAME"...)`.

## 4. Proven gotchas (Boot 4.1 / Jackson 3 / Gradle 9 / Testcontainers 2)
1. MockMvc: `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc` (provided by esm-test-support).
2. Jackson 3: packages are `tools.jackson.*`; inject `tools.jackson.databind.json.JsonMapper`. `JsonNode.asString()` (not `asText`).
3. Spring Data does **not** scan nested repository interfaces: one top-level interface per repository.
4. Hibernate maps Java `int` to `INTEGER`. Use `INTEGER`, not `SMALLINT`, unless the field is `short`.
5. A `@Configuration` class named `XTopics` must not declare a `@Bean` method also named `xTopics` (bean name clash).
6. In ITs, read the Kafka address from the `KafkaAdmin` bean (`kafkaAdmin.getConfigurationProperties().get("bootstrap.servers")`), not from `spring.kafka.bootstrap-servers`.
7. Mockito with primitive `long` parameters: use `anyLong()`, not `any()`.
8. Entities that are never persisted in unit tests have a null id: set it with `ReflectionTestUtils.setField(obj, "id", 1L)`.
9. `HttpStatus.UNPROCESSABLE_CONTENT` (422) is the Spring 7 name. MockMvc: `status().isUnprocessableContent()`.
10. Postgres `format('%s', boolean)` prints `t`. Use `%L` for booleans in seed queries.

## 5. Demo seed from legacy data
- `tools/seed/legacy-db.sh up` starts the legacy DB on localhost:55433 (schema `esmp`; tables listed in `input`'s data dictionary, see `docs/data/data-quality-report.md`).
- Write `tools/seed/queries/<name>.sql` (see `tools/seed/queries/directory-service.sql`): SELECTs that **emit** INSERT statements for *your* tables, keeping legacy IDs, then `setval` for every identity column.
- `tools/seed/export.sh <name>` writes `db/seed/V900__demo_seed.sql`. Verify it applies on top of your schema in a scratch DB (`tools/seed/legacy-db.sh psql -c "CREATE DATABASE x"` …).
- Directory data (users, teams, services, offices) is not seeded in your service: it arrives through the replica topics.

## 6. Rules every service must follow
- Company scoping on every query; foreign records → 404. RBAC via `CurrentUser.require/has`.
- Business events and state snapshots only via `OutboxPublisher` in the business transaction. Sensitive changes go through `AuditPublisher.record(...)`.
- Consumers: `@KafkaListener(groupId = "${spring.application.name}.<purpose>")`; use `EventReader.once(consumer, json, handler)` for domain events; state topics are idempotent upserts.
- Every owned state topic has a `SnapshotSource` (republish on first start) and a `KafkaAdmin.NewTopics` bean.
- Lists: `PageResponse.pageable(page, size, sort)` + `PageResponse.of(...)`. Exports: `CsvWriter.response(...)` + audit `EXPORT`.

## 7. Build and verify (Docker only)
```
ESM_GRADLE_PROJECT_CACHE=.gradle-<name> scripts/build.sh :services:<name>:build > /tmp/<name>-build.log 2>&1; echo $?
grep -E "error:|FAILED|BUILD" /tmp/<name>-build.log
```
Read only the summary lines; failing test details are in `services/<name>/build/test-results/**/*.xml`. "Done" means `:services:<name>:build` (unit + integration tests) is green.
