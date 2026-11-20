# esm-hub Technology Comparison

The alternatives evaluated for each major decision (Technology Stack Standards = master prompt §9; "§N" means §9.N. §16 step 12, §18 "document why alternatives were rejected"). Scoring: ✔ strong fit, ~ acceptable, ✘ weak fit for esm-hub.

## 1. Backend ecosystem (§17: "Enterprise business management system")
| Option | Domain fit | Team/mandate | Ecosystem for workflow, SLA, security | Verdict |
|---|---|---|---|---|
| **Java + Spring Boot** | ✔ transactional, rule-heavy | ✔ mandated | ✔ Security, Data JPA, Kafka, Actuator, Testcontainers | **Selected** |
| .NET / ASP.NET Core | ✔ | ✘ not mandated | ✔ | Rejected: outside the mandated stack |
| Laravel / Symfony | ~ fine for portals | ✘ | ~ weaker fit for async event processing | Rejected |
| Django / FastAPI | ~ (the earlier Python spec in `backup-1training` used FastAPI) | ✘ | ~ | Rejected: client moved to Java |
| NestJS | ~ | ✘ | ~ | Rejected |
| Quarkus / Micronaut | ✔ | ~ Java but not Spring | ~ smaller ecosystem | Rejected: Spring Boot is the mandate and has more support |

## 2. Architecture style
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Modular monolith (one Spring Boot app, modules per bounded context, one PostgreSQL) | Simplest to build, test and operate. ACID across contexts. Fits the expected volume | One deploy unit. Module boundaries must be enforced by tests (e.g. Spring Modulith) | **Preferred on requirements alone** (standard §2.4, §19) |
| **Microservices per bounded context** | Independent deploys and ownership. Fault isolation | About 10 JVMs locally, eventual consistency, heavier operations | **Selected: client mandate** ([ADR-0001](adr/0001-microservices.md)) |
| Serverless functions | Pay per use | Poor fit for long SLA and escalation schedulers. Vendor lock-in | Rejected |

## 3. Messaging (§10)
| Option | Verdict |
|---|---|
| **Apache Kafka (KRaft)** | **Selected**: mandated. Compacted topics give replayable state replicas for directory data and reporting projections |
| RabbitMQ | Viable for the notification fan-out, but no log replay or compaction. Rejected |
| Redis Streams | Adds Redis only for messaging. Rejected (§19, no extra technologies) |
| Cloud queues (SQS/SNS, Service Bus, Pub/Sub) | Cloud-specific (§11). Rejected |
| No broker (synchronous REST) | Would couple service availability. Valid only with a monolith |

## 4. Database (§6)
| Option | Verdict |
|---|---|
| **PostgreSQL 16** | **Selected**: relational, FKs and CHECKs, `TIMESTAMPTZ`, mature, free. One engine for all services |
| MySQL/MariaDB | Viable. Weaker for CHECK/partial-index patterns. Rejected |
| SQL Server / Oracle | Licence cost, and no existing dependency. Rejected |
| MongoDB | The data is relational with integrity rules. Rejected |
| Elasticsearch/OpenSearch for knowledge search | PostgreSQL full-text search is enough at this volume. Can be revisited |

## 5. Frontend (§4)
| Option | Verdict |
|---|---|
| **React + TypeScript + Vite** | **Selected**: mandated. A SPA behind nginx |
| Next.js | SSR/SEO are not needed for an authenticated internal app. Rejected |
| Angular / Vue | Not mandated. Rejected |

## 6. Build, test, deploy
| Concern | Selected | Alternatives rejected |
|---|---|---|
| Build | Gradle 9 ([ADR-0009](adr/0009-gradle.md)) | Maven: replaced at the user's request on 2026-11-19 |
| Migrations | Flyway | Liquibase: XML/YAML overhead brings no benefit here |
| Integration tests | Testcontainers | H2 or embedded Kafka: behaviour differs from production |
| E2E | Playwright | Cypress: weaker multi-browser and parallel support |
| Deploy | Docker Compose | Kubernetes/Helm: not justified at this scale (§19). Can be added later with no code change |
| Auth | Built-in RS256 JWT + JWKS | Keycloak: one more stateful component, and no IdP was given. Kept as the upgrade path |
