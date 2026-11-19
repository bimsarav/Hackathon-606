# Deployment Rules
- Docker-based: a multi-stage Dockerfile per service and for the frontend; `docker compose up -d` runs the whole product (services, gateway, frontend, PostgreSQL, Kafka) with health checks and dependency ordering.
- Images are tagged with the version and git SHA. Containers run as non-root and expose health endpoints.
- `.env.example` documents every variable; real `.env` files are never committed.
- CI pipeline (GitHub Actions) in the repo: build → unit/integration tests → OpenAPI/contract check → vulnerability scan → image build → compose smoke test → Playwright.
- Provide deploy, rollback, backup and restore scripts plus runbooks; Kubernetes manifests/Helm when a cluster target is in scope.
- The README documents every step so a client engineer can build, test, run, deploy and push without AI.
