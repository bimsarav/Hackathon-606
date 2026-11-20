# ADR-0001: Use the python-django stack profile

- **Status:** Accepted (TODO-PRODUCT date)
- **Context:** The Technology Selection Checkpoint (MASTER_PROMPT §9.16) selected this stack (route: TODO-PRODUCT). The workspace keeps verified stack profiles so that selection, version research and compatibility proof are done once.
- **Decision:** Generate the product from `toolkit/stacks/python-django` (Python 3.14, Django 5.2 LTS, DRF, htmx, PostgreSQL 18, uv, Docker). Versions: [COMPATIBILITY_MATRIX.md](../COMPATIBILITY_MATRIX.md).
- **Consequences:** The product starts from a skeleton that already passed its quality gate, Compose smoke test and Trivy scans. The product owns its copy from now on: version changes follow MASTER_PROMPT §9.21 (ADR, matrix update, `scripts/check.sh`).
