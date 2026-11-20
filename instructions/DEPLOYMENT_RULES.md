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

## Server operations & restart resilience (user instruction 2026-11-20, mandatory; full text MASTER_PROMPT §14)
- Inspect the real server and set an enterprise baseline without breaking provider settings (§14.2): patching strategy, firewall, SSH key-only + least privilege, service accounts and permissions, secrets, capacity, disk monitoring + log rotation, time sync, TLS renewal, backups, resource limits, vulnerability scans, monitoring/alerting. Ask before disruptive changes, paid-resource changes or critical config changes.
- Docker (§14.3): engine enabled at boot; `restart: unless-stopped` (or `always`); health checks; readiness-based dependencies (`depends_on: condition: service_healthy` + app-level retry/reconnect), persistent volumes, secrets/certs/mounts available after reboot, graceful shutdown, restart-loop detection, json-file log rotation (max-size/max-file), resource limits sized to the server.
- Recovery (§14.4): readiness reflects real dependency state; scheduled jobs and consumers stay idempotent after recovery; recovery failures produce actionable logs/alerts.
- Restart test (§14.5): record a controlled reboot (12 checks) before declaring deployment complete; if a reboot is not allowed, say so and leave it pending. Never claim it unverified.
- Ongoing operations (§14.6): monitoring, patching, cert expiry, backup integrity, controlled updates with rollback; no unvalidated breaking updates.
- Docs (§14.7) in the product's docs/deployment or docs/operations: SERVER_OPERATIONS, DOCKER_OPERATIONS, STARTUP_AND_RECOVERY, BACKUP_AND_RESTORE, MONITORING_AND_ALERTING, SERVER_RESTART_VERIFICATION, merged into OPERATIONS_RUNBOOK / ROLLBACK_AND_RECOVERY where they already cover the topic.
- Status (§14.8): anything mandatory unverified → `DEPLOYED – OPERATIONAL VERIFICATION PENDING` or `BLOCKED` in execution/DEPLOYMENT_STATUS.md; never "production-ready".

## Incremental delivery (user 2026-11-20)
- Delivery cadence (user 2026-11-20, overrides the one-shot delivery flow): (1) prepare design diagrams first and tell the user where to view them; (2) define an MVP and build it first; (3) host the finished MVP and tell the user how to view it; (4) keep an incremental deployment plan (phases after the MVP) in the product's docs; each later phase starts only with the user's explicit approval. Record the phase gates in execution/DEPLOYMENT_STATUS.md.
- Each phase: plan → user approval → build → test → deploy → verify (§13.9) → report URL → wait for approval of the next phase.
