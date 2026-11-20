# Sample App

TODO-PRODUCT: one paragraph on what Sample App does.

Stack: Python 3.14 · Django 5.2 LTS · Django REST Framework · htmx · PostgreSQL 18 · Docker. Details and versions: [docs/architecture/](docs/architecture/).

## Prerequisites
Docker Engine 20.10+ with Compose v2.21+. Nothing else: Python, uv and all tools run inside containers.

## Run locally
```bash
cp .env.example .env                 # adjust values; never commit .env
docker compose up --build            # http://localhost:8000
docker compose run --rm web python manage.py createsuperuser   # first admin user (admin at /admin/)
```

## Quality gate and tests
```bash
scripts/check.sh               # lint, format, strict types, Django deploy check, migration check, tests (PostgreSQL via Testcontainers)
scripts/smoke.sh               # builds the images, starts the stack, checks the endpoints, tears it down
scripts/check.sh migrations    # after model changes: create migrations
scripts/check.sh lock          # after editing dependencies in pyproject.toml: refresh uv.lock
scripts/check.sh outdated      # dependencies with newer releases
```
Full logs are written to `logs/`.

## Endpoints
| Path | Purpose |
|---|---|
| `/` | Start page |
| `/notes/` | Example feature (login required) |
| `/api/v1/` | REST API (session auth) |
| `/api/schema/`, `/api/docs/` | OpenAPI schema and Swagger UI (login required) |
| `/admin/` | Django admin |
| `/health/live`, `/health/ready` | Liveness; readiness (database) |

## Configuration
All configuration comes from environment variables (see `.env.example`): `DATABASE_URL`, `DJANGO_SECRET_KEY` (required, 50+ random characters in production), `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SECURE_COOKIES`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `LOG_LEVEL`, `LOG_JSON`.

## Deploy
1. Build the image: `docker build -t <registry>/sample-app:<version> .`
2. Provision PostgreSQL 18 (managed service recommended) with backups and point-in-time recovery.
3. Before each release, run migrations: `docker run --rm --env-file <prod.env> <image> python manage.py migrate --noinput`.
4. Run the image behind a TLS-terminating reverse proxy that sets `X-Forwarded-Proto`. Set `DJANGO_SECURE_SSL_REDIRECT=true`, `DJANGO_SECURE_HSTS_SECONDS=31536000` and `DJANGO_SECURE_COOKIES=true`.
5. Health checks: liveness `/health/live`, readiness `/health/ready`.
6. Roll back by redeploying the previous image tag. Migrations should be backward-compatible (expand, then contract) so that the previous version still runs.

CI: `.github/workflows/ci.yml` runs the quality gate, the smoke test and a Trivy scan on every push and pull request.
