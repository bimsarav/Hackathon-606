# Disruption Advisor Compatibility Matrix

From the organisation's stack profile `python-fastapi`. Every version below was resolved from official registries (PyPI, npm, Docker Hub) and proven together by `scripts/verify-profile.sh python-fastapi`: quality gate, Compose smoke test and Trivy. Support dates are from endoflife.date and the projects' own policies. Keep this file in step with `backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`, `frontend/package-lock.json`, the Dockerfiles and `compose.yml` (engineering standards §9.21).

| Technology | Selected version | Runtime it needs | Dependency compatibility | Database compatibility | Build / deploy requirements | Support lifecycle | Known limitations |
|---|---|---|---|---|---|---|---|
| Python (CPython) | 3.14.10 (`python:3.14.10-slim-trixie`, Debian 13) | — | All backend packages ship 3.14 wheels | — | Docker image; no host Python | Security fixes until 2030-10 | 3.15 not adopted yet (ecosystem wheels lag) |
| uv | 0.13.9 (`ghcr.io/astral-sh/uv:0.13.9`) | — | `pyproject.toml` → `uv.lock` | — | Build image only | Active | Pre-1.0 CLI; pin the image tag |
| FastAPI | 0.165.0 (Starlette 1.10.0) | Python 3.11+ | Pydantic 2.14 | — | App factory `app.main:create_app` | Active; 0.x minors may change behaviour | Pin the minor version; re-verify on bump |
| uvicorn (standard) | 0.54.0 | Python 3.10+ | ASGI; `log_config=None` → structlog | — | `python -m app.serve` (workers, proxy headers) | Active | — |
| Pydantic / pydantic-settings | 2.14.4 / 2.16.3 | Python 3.10+/3.11+ | mypy plugin `pydantic.mypy` | — | Settings from environment variables | Active (v2) | — |
| SQLAlchemy | 2.1.9 | Python 3.11+ | psycopg 3 dialect `postgresql+psycopg` | PostgreSQL 18 | Engine per app, session per request | Active (2.x) | Sync sessions by default (async only when justified, §9.3.1) |
| Alembic | 1.20.1 | SQLAlchemy 2.x | `prepend_sys_path = .` needed for the CLI | PostgreSQL 18 | Compose `migrate` service (`alembic upgrade head`) | Active | Autogenerate needs review; `command.check` test guards drift |
| psycopg (binary) | 3.3.9 | Python 3.10+ | SQLAlchemy 2 | PostgreSQL 10–18 | Binary wheel | Active | — |
| PostgreSQL | 18.7 (`postgres:18.7-alpine`) | — | psycopg 3.3 | — | Volume at `/var/lib/postgresql` (18+ layout) | Supported until 2030-11-14 | Single instance in Compose; production: managed PostgreSQL |
| structlog | 26.1.0 | Python 3.10+ | stdlib + uvicorn loggers | — | JSON to stdout | Active | — |
| Node.js (build only) | 26.13.1 (`node:26.13.1-alpine`) | — | Vite 8, Vitest 5, jsdom 31 need Node ≥ 22.12/24.15 | — | Frontend build stage and `scripts/check.sh` | LTS until 2029-04-30 | Not present at runtime |
| React / React DOM | 19.3.1 | Modern browsers | @types/react 19.3 | — | Vite production build | Active | — |
| TypeScript | 7.0.2 | Node (build) | `tsc --noEmit` type check | — | Part of `npm run build` | Active (7.x native compiler) | Some TS 5 options removed; keep `moduleResolution: bundler` |
| Vite / @vitejs/plugin-react | 8.3.8 / 6.3.0 | Node ≥ 20.19 / 22.12 | Vitest 5 | — | `vite build` → `dist/` | Active | — |
| Vitest / Testing Library / jsdom | 5.1.1 / react 16.3.3, dom 10.4.2, jest-dom 8.0.0, user-event 14.6.13 / 31.0.1 | Node ≥ 22.12 | React 19 | — | `npm test` | Active | — |
| nginx | 1.30.7 (`nginx:1.30.7-alpine`), run as non-root `nginx` (uid 101) | — | Proxies `/api/` to `api:8000` | — | `apk upgrade` at build; PID in `/tmp`; listens on 8080 | Stable line 1.30 | `nginxinc/nginx-unprivileged` lagged at 1.30.6 (CVEs) on 2026-11-19; switch back once it catches up |
| pytest / pytest-cov / httpx2 | 9.2.0 / 7.1.0 / 2.16.2 | Python 3.10+ | Starlette 1.x TestClient needs httpx2 (httpx is deprecated there) | — | Run in Docker | Active | — |
| Testcontainers (Python) | 4.15.0 | Docker socket | `testcontainers.community.postgres` | `postgres:18.7-alpine` | Docker 20.10+ host | Active | Needs Docker in CI |
| Ruff / mypy | 0.17.6 / 2.4.1 | — | `known-third-party = ["alembic"]` (local `alembic/` folder) | — | Ruff pinned exactly | Active | — |
| DuckDB (Python) | 2.0.1 | Python 3.11+ (cp314 wheel) | pyarrow 26 (Parquet) | Reads Parquet; independent of PostgreSQL | In the API and ingest images | Active (2.x) | Released 2026-11-20 (patch of 2.0); pinned `>=2.0.1,<2.1` |
| pyarrow | 26.0.1 | Python 3.11+ | DuckDB 2.0, Parquet zstd | — | API image | Active | No type stubs (mypy override) |
| python-calamine | 0.9.1 | Python 3.11+ | Reads .xls (BIFF) and .xlsx | — | API image | Active | — |
| OR-Tools (CP-SAT) | 9.15.6755 | Python 3.9+ (cp314 manylinux wheel) | — | — | API image | Active | Wheel is large (part of the 1 GB API image) |
| Anthropic Python SDK | 2.12.0 | Python 3.10+ | httpx2 (SDK 1.x+) | — | API image; `ANTHROPIC_API_KEY` secret | Active | Model `claude-opus-5-5`; beta `server-side-fallback-2026-07-01`. Phase 3 agent: Messages API tool use with strict schemas, also beta `thinking-display-updates-2026-08-18`; no new package |
| Playwright | 1.65.1 (`mcr.microsoft.com/playwright:v1.65.1`) | Node (in image) | Chromium bundled | — | `scripts/e2e.sh`, Docker | Active | Test-only |
| Trivy | 0.76.2 (`aquasec/trivy`), trivy-action v0.36.0 in CI | — | — | — | CI and `scripts/verify-profile.sh` | Active | — |
| Docker / Compose | Engine 20.10+, Compose v2.21+ | — | — | — | `depends_on: service_completed_successfully` / `service_healthy` | — | — |
