# ADR-0002: Modular monolith with one Django app per bounded context

- **Status:** Accepted (profile default)
- **Context:** MASTER_PROMPT §9.2 and §9.19 forbid microservices without a requirement. Most business systems need strong consistency across contexts and simple operations.
- **Decision:** One deployable Django project. Each bounded context is a Django app under `apps/` that owns its models and migrations. Other apps call its service functions; no app queries another app's tables directly.
- **Consequences:** One image, one database, ACID transactions across contexts, simple deployment. If a context later needs independent scaling, its clear boundary allows extraction (record it in a new ADR).
