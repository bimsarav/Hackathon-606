# Deployment Status — esm-hub (MASTER_PROMPT §13.12)
Overall: **BLOCKED** (no cloud environment provided yet) · Project status: DEPLOYMENT PENDING, not COMPLETED
Updated: 2026-11-20T09:15Z (was 2026-11-20T09:01Z)

| Area | Status | Evidence / notes |
|---|---|---|
| Cloud environment discovery (§13.2) | BLOCKED | 2026-11-20 local check: no cloud CLI (aws/az/gcloud/oci/doctl/kubectl/terraform), no kubeconfig, no cloud credentials or env vars, docker context = local only. Only gh (GitHub) and a Bitbucket SSH host exist. The user will supply the details in a folder inside input/ (possibly mid-build). 2026-11-20: not there yet (input/ has data, existing-code, inbox, problem-domain, reference-material, requirements, solution-documents). Check input/ at every resume/step change |
| Deployment architecture (§13.3) | NOT STARTED | depends on discovery. Candidate today: Docker Compose on one VM is the simplest fit for the existing compose stack; decide after discovery |
| Infrastructure provisioning (§13.4) | NOT STARTED | |
| Application build / images (§13.7) | LOCAL ONLY | clean full build 253 tests (T-005.1); images built locally by compose; not pushed to any registry |
| Deployment (§13.7) | LOCAL ONLY | docker compose stack healthy on the dev machine (http://localhost:8080). Not a cloud deployment |
| Database migrations / seed (§13.6) | LOCAL ONLY | Flyway migrations + demo seed (synthetic) run locally. Synthetic seed must NOT be used as production data without user approval (§13.6) |
| Configuration and secrets (§13.4) | LOCAL ONLY | R/.env with generated secrets (git-ignored); cloud secret manager not chosen yet |
| Security configuration (§13.5) | PARTIAL | JWT auth + RBAC, nginx security headers + login rate limit, only port 8080 published. TLS, cloud firewall/IAM, Trivy image scans pending |
| Health checks (§13.9) | LOCAL ONLY | all 14 containers healthy; API smoke test OK (execution/logs/output/T-005.2-smoke.log) |
| End-to-end tests on the deployed app (§13.9) | LOCAL ONLY | Playwright 6/6 against localhost (execution/logs/output/T-005.2-e2e-run3.log); must be re-run against the cloud URL |
| CI/CD (§13.8) | NOT STARTED | T-006.1 |
| Deployment docs + handover (§13.11) | NOT STARTED | R/docs/architecture/CLOUD_DEPLOYMENT_ARCHITECTURE.md + R/docs/deployment/*.md (path mapping A-CD-1) |

Deployed version: none · Application URL: none · API docs URL: none

## Blockers
- B-002: cloud environment and access not provided (provider, account/project, region, access method, domain/TLS, budget limits)

## Next deployment action
0. At every resume/step change: check input/ for the cloud-details folder; record non-secret details here
1. Before starting deployment: if any of the 5 items is missing, ask the user again for exactly those → run §13.2 discovery and record it in R/docs/deployment/CLOUD_ENVIRONMENT.md
2. Choose the deployment architecture (§13.3, simplest fit) → CLOUD_DEPLOYMENT_ARCHITECTURE.md + ADR
