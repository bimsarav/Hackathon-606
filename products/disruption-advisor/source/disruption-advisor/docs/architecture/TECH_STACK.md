# Disruption Advisor Technology Stack

Selection route: **TODO-PRODUCT** (menu option n · user-specified · autonomous), selected on **TODO-PRODUCT date**. Stack profile: `python-fastapi` (toolkit), generated with `scripts/new-product.sh`.
Related: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) · [TECHNOLOGY_COMPARISON.md](TECHNOLOGY_COMPARISON.md) · [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md) · [adr/](adr/) (the standard's `ARCHITECTURE_DECISIONS/`)

## 1. Product drivers (from the Phase 1 analysis)
TODO-PRODUCT: 5–10 lines. Domain, users and volume, data shape, integrations, security/compliance, hosting constraints and any user-mandated technology. Link the requirements documents instead of repeating them.

## 2. Selected stack
| Layer | Technology | Responsibility |
|---|---|---|
| Backend runtime | Python 3.14 | Single backend runtime (§9.18) |
| API framework | FastAPI (+ Pydantic 2, pydantic-settings) | REST `/api/v1`, validation, OpenAPI 3, problem details |
| Persistence | SQLAlchemy 2 + Alembic + psycopg 3 | ORM, migrations, connection pooling |
| Database | PostgreSQL 18 | System of record |
| ASGI server | uvicorn | HTTP serving with workers and proxy headers |
| Frontend | React 19 + TypeScript 7 + Vite 8 | SPA with typed API client |
| Web server | nginx 1.30 (non-root) | Serves the SPA, proxies `/api/`, security headers |
| Logging | structlog | JSON logs with request ids |
| Quality | Ruff, mypy strict, pytest, Testcontainers, Vitest, Testing Library, `tsc` strict | Gate in `scripts/check.sh` |
| Packaging | uv, npm, Docker multi-stage, Docker Compose | Reproducible builds; one-command local stack |
| Security scanning | Trivy (CI) | Dependencies, secrets, misconfiguration, images |

## 3. Product-specific additions
TODO-PRODUCT: authentication (ADR 0004 is mandatory), background jobs, caching, and so on, each with its ADR. Remove this section if none.

## 4. Deviations from MASTER_PROMPT §9
None in the profile. TODO-PRODUCT: list any product deviation with its reason and mitigation.
