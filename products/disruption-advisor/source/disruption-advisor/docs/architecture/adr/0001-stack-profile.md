# ADR-0001: Use the python-fastapi stack profile

- **Status:** Accepted (2026-11-20)
- **Context:** The Technology Selection Checkpoint (engineering standards §9.16) selected this stack (route: autonomous, authorised by the user, Q18). The organisation keeps verified stack profiles so that selection, version research and compatibility proof are done once.
- **Decision:** Generate the product from the organisation's verified `python-fastapi` stack profile (Python 3.14, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 18, React 19 + TypeScript + Vite, nginx, uv, npm, Docker). Versions: [COMPATIBILITY_MATRIX.md](../COMPATIBILITY_MATRIX.md).
- **Consequences:** The product starts from a skeleton that already passed its quality gate, Compose smoke test and Trivy scans. The product owns its copy from now on: version changes follow engineering standards §9.21 (ADR, matrix update, `scripts/check.sh`).
