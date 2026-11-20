# Deployment Rules
- Docker-based: a multi-stage Dockerfile per service and for the frontend; `docker compose up -d` runs the whole product (services, gateway, frontend, PostgreSQL, Kafka) with health checks and dependency ordering.
- Images are tagged with the version and git SHA. Containers run as non-root and expose health endpoints.
- `.env.example` documents every variable; real `.env` files are never committed.
- CI pipeline (GitHub Actions) in the repo: build → unit/integration tests → OpenAPI/contract check → vulnerability scan → image build → compose smoke test → Playwright.
- Provide deploy, rollback, backup and restore scripts plus runbooks; Kubernetes manifests/Helm when a cluster target is in scope.
- The README documents every step so a client engineer can build, test, run, deploy and push without AI.

## Cloud deployment (user instruction 2026-11-20, mandatory; full text MASTER_PROMPT §13)
- A product is delivered only when it is **deployed, running and verified in the cloud environment provided by the user**, and the user has the URL and handover information. Code, images, IaC or instructions alone are not completion.
- Discover the real environment first (§13.2). Never assume a provider; never invent credentials, resources, URLs or results. If access is missing, request it, finish all safe work, and mark the project BLOCKED / DEPLOYMENT PENDING.
- Choose the simplest architecture that fits (§13.3); no Kubernetes or extra cloud services without a justification. Secrets come from the provider's secret manager or a secure alternative; separate dev/test/staging/prod config.
- Security before exposure (§13.5): HTTPS with valid TLS, least privilege, only the entry point exposed, image and dependency scans.
- Data (§13.6): never run destructive operations on existing data without explicit approval; synthetic seed data is not production data unless the user approves.
- Verify the deployed app (§13.9: infrastructure, application, end-to-end, operational) and record it.
- Documents (§13.11, path mapping A-CD-1): product repo docs/architecture/CLOUD_DEPLOYMENT_ARCHITECTURE.md and docs/deployment/{CLOUD_ENVIRONMENT, DEPLOYMENT_ARCHITECTURE, DEPLOYMENT_GUIDE, ENVIRONMENT_CONFIGURATION, CI_CD, SECURITY_CONFIGURATION, POST_DEPLOYMENT_VERIFICATION, OPERATIONS_RUNBOOK, ROLLBACK_AND_RECOVERY}.md.
- State: execution/DEPLOYMENT_STATUS.md (§13.12), updated at every deployment change and read on every resume.
- Cloud environment input (user instruction 2026-11-20): the cloud details (provider, account/project, region, access method, domain/TLS, limits, demo-data approval) arrive in a separate folder inside `input/`, possibly in the middle of a build. At every resume and step change, check `input/` for a new folder or files with cloud or deployment details and, when found, record them in `execution/DEPLOYMENT_STATUS.md` and the product's `docs/deployment/CLOUD_ENVIRONMENT.md` (never copy secrets). Before starting deployment (Phase 6 / T-008), if any of the 5 items is still missing, ask the user again for exactly the missing items. Never assume them.
