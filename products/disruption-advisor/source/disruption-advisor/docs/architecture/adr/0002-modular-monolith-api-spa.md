# ADR-0002: Modular monolith API with a separate SPA, one origin through nginx

- **Status:** Accepted (2026-11-20)
- **Context:** Microservices add operational cost and are only justified by a concrete requirement; there is none here. The product needs a rich client UI and an API that other systems can use.
- **Decision:** One FastAPI service (bounded contexts as packages or routers inside it) and one React SPA. nginx serves the SPA and proxies `/api/`, so browser and API share one origin: no CORS, and cookie-based auth stays possible. Synchronous SQLAlchemy sessions, one per request; async only where a requirement justifies it.
- **Consequences:** Two images plus the database; a clear API contract (OpenAPI) that serves the SPA and integrations alike. Extract a service later only through a new ADR.
