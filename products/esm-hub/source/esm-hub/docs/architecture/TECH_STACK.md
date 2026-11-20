# esm-hub Technology Stack

This document follows the organisation's Technology Stack & Engineering Standards (master prompt §9; "§N" below means §9.N), selection process §16. Alternatives considered: [TECHNOLOGY_COMPARISON.md](TECHNOLOGY_COMPARISON.md). Versions and support status: [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md). Decisions: [adr/](adr/) (this is the standard's `ARCHITECTURE_DECISIONS/` folder).

## 1. Problem domain and drivers (§16.1)

**Selection route:** user-specified stack (§16.4), mandated by the client on 2026-11-19. No selection menu was presented, because the stack was fixed before the selection workflow existed. System architecture: [architecture.md](architecture.md) (this product's `SYSTEM_ARCHITECTURE.md`).
| Driver | esm-hub |
|---|---|
| Domain | Enterprise Service Management (ITSM-style): incidents with business-hours SLAs, problems, service requests with approvals, changes with CAB, assets, knowledge, notifications, audit, reporting ([requirements-analysis.md](../business/requirements-analysis.md)) |
| Users and boundaries | Employees, agents, team leads, approvers, CAB, admins across four offices (Abu Dhabi, Dubai, London, Colombo) and several companies. Company-scoped data (NFR-1) |
| Data | Strongly relational, transactional records with an audit trail. Moderate volume: the legacy dump holds hundreds of tickets, and growth is expected to stay in the thousands to low millions of rows. No big-data or search-engine workload |
| Non-functional | 99.5 % availability, RTO 4 h, RPO 24 h (BQ-10, pending PO approval); structured logs and correlation IDs; health checks; idempotent creates; accessibility; per-office timezones |
| Integration | Email (SMTP) only. Internal events: domain events consumed by notification, audit and reporting |
| Hosting | Docker Compose locally and for the demo. Production: a container host with managed PostgreSQL behind a TLS proxy. Cloud-neutral |
| Client constraint | The client mandated Java/Spring Boot **microservices**, **Kafka**, React, JUnit 5/Mockito/Testcontainers, Playwright and Docker (user instruction 2026-11-19). The stack was therefore fixed before this standard existed; see §3 |

## 2. Selected stack
| Layer | Selection | Why |
|---|---|---|
| Language/runtime | Java (OpenJDK 27) | Mandated "latest stable GA". Strong typing and a mature ecosystem for transactional enterprise systems (§17 "enterprise business management") |
| Backend framework | Spring Boot 4.1 (Spring Framework 7), Spring Security, Spring Data JPA/Hibernate | Production-proven. Built-in validation, OAuth2 resource server, Actuator and Flyway integration |
| Edge | Spring Cloud Gateway (2025.1) | One entry point: routing, request ID, login rate limit |
| Service split | 9 domain services + gateway, database-per-service ([ADR-0001](adr/0001-microservices.md)) | Client mandate. Bounded contexts follow the ESM sub-domains |
| Messaging | Apache Kafka 4.4 (KRaft, no ZooKeeper) with transactional outbox, idempotent consumers and DLTs ([ADR-0004](adr/0004-async-integration.md), [ADR-0005](adr/0005-outbox.md)) | Mandated. Fits the real fan-out: one ticket event feeds notification, audit and reporting. Compacted state topics replace synchronous service-to-service calls |
| Database | PostgreSQL 16, one database per service, Flyway migrations | Relational data with constraints and FKs (§6). One engine for all services, so there are no extra databases |
| API | REST + OpenAPI 3 (springdoc), `/api/v1`, problem+json errors, `Idempotency-Key` | §9 defaults. No need for GraphQL or gRPC |
| AuthN/Z | RS256 JWT issued by directory-service, JWKS, role-based access + company scoping ([ADR-0002](adr/0002-jwt.md)) | No external IdP is available. Can be swapped for OIDC (Keycloak or Entra ID) later |
| Frontend | React 19 + TypeScript + Vite | Mandated. A component-based SPA; server rendering is not needed |
| Build | Gradle 9 (wrapper, Kotlin DSL, version catalog, buildSrc) ([ADR-0009](adr/0009-gradle.md)); npm for the frontend | User instruction. Reproducible because builds run inside Docker (`scripts/build.sh`) |
| Tests | JUnit 5, Mockito, Spring test slices, Testcontainers (PostgreSQL, Kafka), Playwright | §13 Java + browser rows |
| Observability | SLF4J/Logback JSON (ECS), `X-Request-ID` correlation, Actuator health/readiness, Micrometer → Prometheus | §14. OpenTelemetry tracing is a documented next step |
| Security tooling | Trivy (dependencies + images) in CI | §12. Gitleaks/Semgrep can be added as CI steps |
| Packaging/deploy | Docker images (`eclipse-temurin:27-jre`, non-root), Docker Compose, GitHub Actions | §11. Kubernetes is **not** used because Compose is enough for the stated scale (§19) |
| Email (local) | Mailpit | SMTP sink with a UI for demo and testing only |

## 2a. Data engineering assessment (§22.3)
**No separate data engineering platform is required.** The data needs are covered inside the application stack:
- Cross-domain reporting (FR-13) uses a CQRS read model: reporting-service consumes the Kafka state topics into its own PostgreSQL projections and computes KPIs in SQL ([ADR-0007](adr/0007-cqrs-reporting.md)). The volume is moderate and near-real-time is enough, so no warehouse, stream processor or orchestrator is needed.
- The legacy dump is a one-off import, repaired and turned into per-service seed migrations ([ADR-0008](adr/0008-legacy-seed.md)), not a recurring pipeline. Data-quality findings: [data-quality-report.md](../data/data-quality-report.md).
- Revisit this if the PO asks for historical analytics across years, external BI tools on raw data, or continuous sync with other systems. That would trigger §22.3 (likely batch ELT into an analytical store).

## 3. Deviations from the standard, recorded openly
| Standard | Deviation | Reason and mitigation |
|---|---|---|
| §2.6 / §19 "no microservices or distributed messaging unless justified by requirements" | Microservices + Kafka | Client mandate (user decision, PRODUCT_RULES §3). On requirements alone, a modular Spring Boot monolith with PostgreSQL would be the simpler fit (see the comparison). Mitigation: shared libs and conventions, one Compose file, no synchronous service coupling |
| §2.2 / §3.3 "Java – supported LTS release" | OpenJDK 27 (non-LTS) | The rule was "latest stable GA". JDK 27 is superseded by 28 in March 2027. Mitigation: the code uses no 26/27-only APIs. Moving to JDK 25 LTS is a one-line change in `gradle/libs.versions.toml` plus the base images. **Recommended before production** (open decision for the PO) |
| §20 "maintain dependency lock files" | Gradle dependency locking is not yet enabled | Versions are pinned through the catalog and the Spring Boot BOM. Enabling `dependencyLocking` is tracked for T-006.1. The frontend commits `package-lock.json` |

## 4. Approval
The stack is approved by the client mandate (2026-11-19). The JDK LTS question and BQ-1..10 are pending PO approval.
