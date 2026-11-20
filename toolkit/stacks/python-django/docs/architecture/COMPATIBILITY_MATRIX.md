# Sample App Compatibility Matrix

From stack profile `python-django` (toolkit). Every version below was resolved from official registries (PyPI, Docker Hub, npm) and proven together by `scripts/verify-profile.sh python-django`: quality gate, Compose smoke test and Trivy. Support dates are from endoflife.date and the projects' own policies. Keep this file in step with `pyproject.toml`, `uv.lock`, `Dockerfile` and `compose.yml` (MASTER_PROMPT §9.21).

| Technology | Selected version | Runtime it needs | Dependency compatibility | Database compatibility | Build / deploy requirements | Support lifecycle | Known limitations |
|---|---|---|---|---|---|---|---|
| Python (CPython) | 3.14.10 (`python:3.14.10-slim-trixie`, Debian 13) | — | All packages below ship 3.14 wheels | — | Docker image; no host Python | Security fixes until 2030-10 | 3.15 not adopted yet (released 2026-10; ecosystem wheels lag) |
| uv | 0.13.9 (`ghcr.io/astral-sh/uv:0.13.9`) | — | Reads `pyproject.toml`, writes `uv.lock` | — | Copied into the build image only | Active, frequent releases | Pre-1.0 CLI; pin the image tag |
| Django | 5.2.19 (LTS) | Python 3.10–3.14 | DRF 3.18, drf-spectacular 0.30, django-stubs 5.2 | PostgreSQL 14+ (psycopg 3) | `manage.py migrate` (Compose `migrate` service), `collectstatic` at image build | LTS, security fixes until 2028-04-30 | Deliberately held below 6.x (see `freshness.conf`) |
| Django REST Framework | 3.18.3 | Django 4.2–6.x | drf-spectacular 0.30 | — | — | Active | — |
| drf-spectacular | 0.30.0 | DRF 3.x | Requires DRF's `DEFAULT_SCHEMA_CLASS` setting | — | — | Active | Swagger UI assets load from a CDN |
| psycopg (binary) | 3.3.9 | Python 3.10+ | Django's PostgreSQL backend | PostgreSQL 10–18 | Binary wheel, no libpq build | Active | — |
| PostgreSQL | 18.7 (`postgres:18.7-alpine`) | — | psycopg 3.3 | — | Volume mounted at `/var/lib/postgresql` (18+ layout) | Supported until 2030-11-14 | Single instance in Compose; production: managed PostgreSQL with backups |
| gunicorn | 27.0.1 | Python 3.10+ | WSGI (`config.wsgi`) | — | 3 workers by default | Active | Sync workers: keep slow I/O in background jobs |
| whitenoise | 6.12.0 | Django 4.2+ | `CompressedManifestStaticFilesStorage` | — | Needs `collectstatic` (done in the image) | Active | Tests use plain storage (no manifest) |
| htmx | 2.0.11 (vendored `static/vendor/htmx.min.js`) | Modern browsers | CSRF header set in `base.html` | — | No Node build | Active (2.x) | — |
| structlog | 26.1.0 | Python 3.10+ | stdlib logging bridge | — | JSON to stdout | Active | — |
| django-environ | 0.14.0 | Python 3.9+ | — | `DATABASE_URL` parsing | — | Active | No type stubs (one `type: ignore`) |
| pytest / pytest-django / pytest-cov | 9.2.0 / 4.14.0 / 7.1.0 | Python 3.10+ | Django 5.2 | Test DB from Testcontainers | Run in Docker | Active | — |
| Testcontainers (Python) | 4.15.0 | Docker socket | `testcontainers.community.postgres` | `postgres:18.7-alpine` | Docker 20.10+ host | Active | Needs Docker in CI (GitHub-hosted runners have it) |
| Ruff | 0.17.6 | — | — | — | Pinned exactly (rule sets change between minors) | Active | — |
| mypy + django-stubs + DRF stubs | 1.19.1 + 5.2.9 + 3.16.9 | Python 3.14 | `compatible-mypy` extra pins mypy for django-stubs 5.2 | — | — | Active | mypy 2.x arrives with django-stubs 6.x (with Django 6.2 LTS) |
| Trivy | 0.76.2 (`aquasec/trivy`), trivy-action v0.36.0 in CI | — | — | — | CI step and `scripts/verify-profile.sh` | Active | — |
| Docker / Compose | Engine 20.10+, Compose v2.21+ | — | — | — | `depends_on: service_completed_successfully` | — | — |
