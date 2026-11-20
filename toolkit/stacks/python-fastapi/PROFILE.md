# Profile: python-fastapi: FastAPI API + React SPA

Menu card for the Technology Selection Checkpoint (MASTER_PROMPT §9.16.2–§9.16.3). Copy the summary into the numbered menu; this file holds the full detail. Versions: [docs/architecture/COMPATIBILITY_MATRIX.md](docs/architecture/COMPATIBILITY_MATRIX.md). Last verification: [VERIFIED.md](VERIFIED.md).

## Menu summary (paste into the selection menu)
**Python FastAPI + React SPA**: typed FastAPI backend (SQLAlchemy 2, Alembic, PostgreSQL 18) and a React 19 + TypeScript SPA served by nginx. Best for API-first products, rich interactive UIs, integrations and Python/AI-adjacent services. Limits: two runtimes (Python + Node build), and you build auth/admin yourself. Complexity: **medium**.

## Stack (all §9.16.2 fields)
| Field | Selection |
|---|---|
| Backend language and framework | Python 3.14, FastAPI (application factory, lifespan-managed engine), Pydantic 2 + pydantic-settings; modular monolith |
| Frontend | React 19 + TypeScript 7 + Vite 8 SPA; loading/empty/error/success states; accessible markup; served by nginx 1.30 (non-root, CSP and security headers) |
| Database | PostgreSQL 18 |
| ORM / persistence | SQLAlchemy 2 (typed `Mapped[...]`, sync sessions per request); Alembic migrations, with a test that fails when models and migrations differ |
| API and integration | REST under `/api/v1`, OpenAPI 3 at `/api/openapi.json` (Swagger UI `/api/docs`); RFC 9457 problem details for every error; bounded paging |
| Authentication and authorization | **Product decision** (ADR 0004): recommended OIDC (Keycloak, Entra ID, Auth0, ...) with bearer-token validation as a FastAPI dependency. The skeleton ships no auth |
| Messaging / background jobs | None by default. Add a broker/worker only when a requirement needs it (§9.10) |
| Testing | pytest + FastAPI TestClient (httpx2); Testcontainers PostgreSQL 18 migrated with Alembic; Vitest + Testing Library (jsdom) for the SPA |
| Build and dependencies | uv (`uv.lock`) and npm (`package-lock.json`); everything runs in Docker (`scripts/check.sh`) |
| Containers and deployment | API image (multi-stage, non-root, OS updates, no pip at runtime, uvicorn via `python -m app.serve`); web image (Node build → nginx); Docker Compose with a one-shot `migrate` service |
| Monitoring and logging | structlog JSON logs with a request id (pure-ASGI middleware, `X-Request-ID`); `/health/live`, `/health/ready`; container healthchecks |
| Security tooling | Ruff security rules (`S`), mypy strict (pydantic plugin), CSP/nosniff/frame headers, Trivy (dependencies, secrets, misconfiguration, images) in CI |
| Quality tooling | Ruff (lint + format), mypy strict, `tsc` strict (`noUncheckedIndexedAccess`) |

## Fit
- **Use for:** API-first platforms and SaaS, products with a rich interactive UI, integration hubs, data/AI-adjacent services (Python ecosystem), mobile backends (§9.17).
- **Avoid for:** admin-heavy internal tools where Django's built-ins would save weeks (use python-django), CMS/e-commerce (use a dedicated platform), JVM/.NET enterprise mandates.
- **Key advantages:** typed end to end (Pydantic, SQLAlchemy 2, TypeScript); automatic OpenAPI; clean separation of API and UI; async available where it genuinely helps.
- **Limitations and trade-offs:** two toolchains (Python + Node); no built-in auth, admin or forms; FastAPI is pre-1.0 (0.x minors can change behaviour, so pin and re-verify); SPA adds client-side complexity.
- **Implementation complexity:** medium. **Long-term maintainability:** high with the strict gates; watch FastAPI 0.x and TypeScript major releases (re-run `scripts/verify-profile.sh`).

## Use it
```
scripts/check-stack-freshness.sh python-fastapi    # must say FRESH (else bump by ADR + scripts/verify-profile.sh)
scripts/new-product.sh python-fastapi <product-name>
```
Then fill the `TODO-PRODUCT` parts of `docs/architecture/*.md`, decide authentication (ADR 0004), replace the notes example, and keep `scripts/check.sh` green.
