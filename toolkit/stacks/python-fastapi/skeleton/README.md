# Sample App

TODO-PRODUCT: one paragraph on what Sample App does.

Stack: Python 3.14 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 18 · React 19 + TypeScript + Vite · nginx · Docker. Details and versions: [docs/architecture/](docs/architecture/).

## Prerequisites
Docker Engine 20.10+ with Compose v2.21+. Nothing else: Python, uv, Node and all tools run inside containers.

## Run locally
```bash
cp .env.example .env                 # adjust values; never commit .env
docker compose up --build            # http://localhost:8080  (API docs: http://localhost:8080/api/docs)
```

## Quality gate and tests
```bash
scripts/check.sh            # backend: lint, format, strict types, tests (PostgreSQL via Testcontainers, Alembic)
                            # frontend: npm ci, type check, unit tests, production build
scripts/smoke.sh            # builds the images, starts the stack, exercises nginx → API → database, tears it down
scripts/check.sh lock       # after editing dependencies: refresh backend/uv.lock and frontend/package-lock.json
scripts/check.sh outdated   # dependencies with newer releases
```
Full logs are written to `logs/`.

Migrations after model changes (inside the backend dev image or any environment with the backend installed):
`alembic revision --autogenerate -m "<change>"`. Review the generated file; the test suite fails while models and migrations differ.

## Endpoints (through the web container)
| Path | Purpose |
|---|---|
| `/` | React SPA |
| `/api/v1/notes` | Example feature (REST) |
| `/api/openapi.json`, `/api/docs` | OpenAPI schema and Swagger UI |
| `/healthz` | nginx health |
| API container: `/health/live`, `/health/ready` | Liveness; readiness (database) |

## Configuration
Environment variables (see `.env.example`): `DATABASE_URL` (`postgresql+psycopg://...`), `LOG_LEVEL`, `LOG_JSON`, `WORKERS` (`API_WORKERS` in Compose), `DB_POOL_SIZE`.

## Deploy
1. Build both images: `docker build -t <registry>/sample-app-api:<version> backend` and `docker build -t <registry>/sample-app-web:<version> frontend`.
2. Provision PostgreSQL 18 (managed service recommended) with backups and point-in-time recovery.
3. Before each release, run migrations: `docker run --rm -e DATABASE_URL=... <api image> alembic upgrade head`.
4. Run `api` (internal only) and `web` (port 8080) behind a TLS-terminating reverse proxy. `web` must reach `api` at `http://api:8000` (or change `proxy_pass` in `frontend/nginx.conf`).
5. Health checks: web `/healthz`; API `/health/live` (liveness), `/health/ready` (readiness).
6. Roll back by redeploying the previous image tags. Write migrations to be backward-compatible (expand, then contract).

CI: `.github/workflows/ci.yml` runs the quality gate, the smoke test and a Trivy scan on every push and pull request.
