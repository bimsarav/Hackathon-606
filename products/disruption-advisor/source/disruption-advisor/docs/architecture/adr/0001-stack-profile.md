# ADR-0001: Python FastAPI + React + PostgreSQL stack

- **Status:** Accepted (2026-11-20)
- **Context:** Three candidate stacks were compared on functional fit, security, maintainability, architecture, performance and cost (docs/architecture/TECHNOLOGY_COMPARISON.md). The product needs strong data-processing and optimisation libraries, an interactive UI for what-if analysis, and a small operational footprint.
- **Decision:** Python 3.14 with FastAPI, SQLAlchemy 2 and Alembic on PostgreSQL 18; React 19 + TypeScript + Vite served by nginx; uv, npm and Docker for builds. Versions: docs/architecture/COMPATIBILITY_MATRIX.md.
- **Consequences:** One API-first engine serves the SPA and can be reused by other systems. Two toolchains (Python and Node) are maintained. Version changes are recorded in an ADR and the compatibility matrix, and pass `scripts/check.sh` before release.
