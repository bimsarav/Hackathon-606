# Profile: python-django: Django modular monolith, server-rendered with htmx

Menu card for the Technology Selection Checkpoint (MASTER_PROMPT §9.16.2–§9.16.3). Copy the summary into the numbered menu; this file holds the full detail. Versions: [docs/architecture/COMPATIBILITY_MATRIX.md](docs/architecture/COMPATIBILITY_MATRIX.md). Last verification: [VERIFIED.md](VERIFIED.md).

## Menu summary (paste into the selection menu)
**Python Django modular monolith**: Django 5.2 LTS + Django REST Framework, server-rendered pages with htmx, PostgreSQL 18, one container plus a database. Best for business, admin-heavy and internal applications that need auth, admin screens and forms quickly. Limits: no SPA-grade interactivity, and synchronous request handling by default. Complexity: **low**.

## Stack (all §9.16.2 fields)
| Field | Selection |
|---|---|
| Backend language and framework | Python 3.14, Django 5.2 LTS (modular monolith: one Django project, one app per bounded context under `apps/`) |
| Frontend | Server-rendered Django templates + htmx 2 (vendored, no Node build); accessible base layout, skip link, focus styles, dark mode |
| Database | PostgreSQL 18 |
| ORM / persistence | Django ORM; schema changes only through Django migrations (`makemigrations --check` in the gate) |
| API and integration | REST under `/api/v1/` with Django REST Framework; OpenAPI 3 via drf-spectacular (`/api/schema/`, `/api/docs/`); limit/offset pagination |
| Authentication and authorization | Django auth (sessions, PBKDF2 password hashing, 12-character minimum, CSRF); DRF `IsAuthenticated` by default; per-owner query filtering in the example. OIDC/SSO via a product ADR when needed |
| Messaging / background jobs | None by default. Add Celery + Redis (or Django tasks) only when a requirement needs async work (§9.10) |
| Testing | pytest + pytest-django; Testcontainers PostgreSQL 18 for integration tests (no SQLite stand-in); coverage report |
| Build and dependencies | uv (lock file `uv.lock`, `pyproject.toml`); everything runs in Docker (`scripts/check.sh`), no local Python needed |
| Containers and deployment | Multi-stage Dockerfile (non-root, healthcheck, OS updates, no pip at runtime); gunicorn; whitenoise for static files; Docker Compose with a one-shot `migrate` service |
| Monitoring and logging | structlog JSON logs with a request id (`X-Request-ID`); `/health/live` and `/health/ready` (database); container healthchecks |
| Security tooling | Ruff security rules (bandit set `S`), mypy strict, `manage.py check --deploy`, Trivy (dependencies, secrets, misconfiguration, images) in CI |
| Quality tooling | Ruff (lint + format), mypy strict with django-stubs and DRF stubs |

## Fit
- **Use for:** enterprise/business management, internal tools, back-office and admin-heavy systems, CRUD-rich portals, content-backed apps, MVPs that must ship fast with auth and admin out of the box (§9.17).
- **Avoid for:** highly interactive SPAs or offline-first clients (use python-fastapi + React), very high-concurrency realtime/websocket workloads, ML model serving.
- **Key advantages:** batteries included (auth, admin, forms, ORM, migrations, CSRF); one runtime and one container; very low operational complexity; LTS line supported to April 2028.
- **Limitations and trade-offs:** htmx suits form-and-list UIs, not rich client state; Django's sync request model needs care for slow I/O (use background jobs); the 5.2 LTS line deliberately trails Django 6.x features.
- **Implementation complexity:** low. **Long-term maintainability:** high (stable LTS cadence every 2 years, large ecosystem, strict typing in the gate).

## Use it
```
scripts/check-stack-freshness.sh python-django     # must say FRESH (else bump by ADR + scripts/verify-profile.sh)
scripts/new-product.sh python-django <product-name>
```
Then fill the `TODO-PRODUCT` parts of `docs/architecture/*.md`, replace `apps/notes` with the product's own apps, and keep `scripts/check.sh` green.
