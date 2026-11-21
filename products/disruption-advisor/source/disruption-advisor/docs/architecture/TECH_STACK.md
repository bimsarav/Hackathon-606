# Disruption Advisor Technology Stack

Selection route: **autonomous** (user answer Q18 "You choose", 2026-11-20), selected on **2026-11-20**. Stack profile: `python-fastapi` (toolkit), generated with `scripts/new-product.sh`.
Related: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) · [TECHNOLOGY_COMPARISON.md](TECHNOLOGY_COMPARISON.md) · [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md) · [adr/](adr/) (the standard's `ARCHITECTURE_DECISIONS/`)

## 1. Product drivers (from the Phase 1 analysis)
- **Domain:** airline disruption management for OCC and PCU (UC5): delay impact along aircraft rotations, recovery options, passenger priority and seat-aware re-accommodation. Recommend-only, human approval (Q21).
- **Data:** batch airline extracts: 27.9M booking rows, rotation, inventory, MCT, punctuality. Read-mostly, analytical, columnar. Treated as real passenger data (Q3).
- **Volume and users:** a handful of concurrent OCC/PCU users; analyses must answer within seconds.
- **Integrations:** none live in the MVP (file extracts). The Anthropic Claude API is optional, for wording.
- **Security and compliance:** personal data (names, assistance codes), EU261, GDPR Art. 22 (explanations and human review).
- **Hosting:** the provided OCI VM with Docker Compose (engineering standards §13/§14).
- **Mandated technology:** Parquet for tabular data (§9.25).

Requirements: the UC5 use-case document, the briefing transcript, the product-owner Q&A of 2026-11-20 and the clarification register (Q1–Q30), held by the project team.

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
| Addition | Version | Responsibility | ADR |
|---|---|---|---|
| DuckDB over Apache Parquet (pyarrow, python-calamine for .xls/.xlsx) | 2.0.1 / 26.0.1 / 0.9.1 | Ingest extracts once into typed Parquet; in-memory analytical queries | [0005](adr/0005-parquet-duckdb-analytics-store.md) |
| Google OR-Tools CP-SAT | 9.15 | Seat-limited re-accommodation (0/1 assignment, PNR groups together) | [0006](adr/0006-or-tools-cp-sat-rebooking.md) |
| Anthropic Python SDK, model `claude-opus-5-5` (configurable) | 2.12 | Grounded explanations and message drafts; template fallback; server-side refusal fallback. Phase 3: the recommend-only agent (Messages API tool use, manual loop, rule-based planner fallback); same SDK, no new dependency | [0007](adr/0007-generative-ai-grounded-explanations.md), [0010](adr/0010-tool-using-agent.md) |
| Demo authentication (stdlib HMAC tokens, two roles) + nginx login rate limit | n/a | MVP access control | [0004](adr/0004-authentication.md) |
| Playwright | 1.65.1 | End-to-end tests (Docker image `mcr.microsoft.com/playwright:v1.65.1`) | n/a (testing standard) |
| One-shot `ingest` Compose service | n/a | Builds the Parquet operating picture before the API starts | [0005](adr/0005-parquet-duckdb-analytics-store.md) |

## 4. Deviations from engineering standards §9
- **No predictive ML in the MVP** (§9.8, §9.23): decisions use rules and optimisation. A learned model would need labelled history we do not have, and could not guarantee passenger-rights constraints. Delay prediction (LightGBM + SHAP) is phase 2 (docs/delivery/MVP_AND_INCREMENTAL_PLAN.md).
- **Demo authentication instead of OIDC** (ADR 0004 recommends OIDC): no identity provider was supplied. Mitigation: random passwords in server secrets, signed expiring tokens, login rate limit, HTTPS in phase 2, OIDC before production.
- **No CI/CD deployment in the MVP** (§13.8): the profile's CI workflow runs the quality gate; deployment is scripted and manual until phase 4.
