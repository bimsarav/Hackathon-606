# Sample App Technology Stack

Selection route: **TODO-PRODUCT** (menu option n · user-specified · autonomous), selected on **TODO-PRODUCT date**. Stack profile: `python-django` (toolkit), generated with `scripts/new-product.sh`.
Related: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) · [TECHNOLOGY_COMPARISON.md](TECHNOLOGY_COMPARISON.md) · [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md) · [adr/](adr/) (the standard's `ARCHITECTURE_DECISIONS/`)

## 1. Product drivers (from the Phase 1 analysis)
TODO-PRODUCT: 5–10 lines. Domain, users and volume, data shape, integrations, security/compliance, hosting constraints and any user-mandated technology. Link the requirements documents instead of repeating them.

## 2. Selected stack
| Layer | Technology | Responsibility |
|---|---|---|
| Runtime | Python 3.14 | Single backend runtime (§9.18) |
| Web framework | Django 5.2 LTS | Routing, views, forms, auth, admin, ORM, migrations, security middleware |
| API | Django REST Framework + drf-spectacular | REST `/api/v1/`, OpenAPI 3 schema and docs |
| UI | Django templates + htmx 2 | Server-rendered pages with partial updates; no separate frontend build |
| Database | PostgreSQL 18 | System of record; constraints, indexes, transactions |
| Static files | whitenoise | Compressed, cache-busted static files from the app container |
| App server | gunicorn | WSGI process manager |
| Logging | structlog | JSON logs with request ids |
| Quality | Ruff, mypy strict (django-stubs), pytest, pytest-django, Testcontainers | Gate in `scripts/check.sh` |
| Packaging | uv, Docker multi-stage, Docker Compose | Reproducible builds; one-command local stack |
| Security scanning | Trivy (CI) | Dependencies, secrets, misconfiguration, images |

## 3. Product-specific additions
TODO-PRODUCT: anything added on top of the profile (for example Celery + Redis for background jobs, OIDC login), each with its ADR. Remove this section if none.

## 4. Deviations from MASTER_PROMPT §9
None in the profile. TODO-PRODUCT: list any product deviation with its reason and mitigation.
