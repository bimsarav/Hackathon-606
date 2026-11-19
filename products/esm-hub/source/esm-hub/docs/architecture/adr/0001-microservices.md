# ADR-0001: Microservices per bounded context, database-per-service

- **Status:** Accepted (2026-11-19)
- **Context:** The client mandates Spring Boot microservices. ESM has clear sub-domains (identity/org, incidents+SLA+problems, requests, changes, assets, knowledge, notifications, audit, reporting).
- **Decision:** Nine domain services plus a gateway. Each owns its PostgreSQL database; no service reads another's tables.
- **Consequences:** Independent deployability and clear ownership. Cost: more moving parts, eventual consistency between contexts, and a heavier local stack (about 10 JVMs).
