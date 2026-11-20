# Deployment Status — esm-hub (MASTER_PROMPT §13.12)
Overall: **DEPLOYMENT PENDING** — environment discovered, dry run passed, decisions D-A/D-B taken (D-011, D-012); a production bootstrap must be built before deploying
Updated: 2026-11-20T11:40Z

| Area | Status | Evidence / notes |
|---|---|---|
| Cloud environment discovery (§13.2) | DONE | OCI eu-frankfurt-1, VM.Standard.E4.Flex x86_64, 8 vCPU / 62 GiB / 67 GB free, Oracle Linux 10.2, Docker 29 + Compose v5 enabled at boot, firewalld open 22/80/443/8080/8888/5432, passwordless sudo, outbound OK. R/docs/deployment/CLOUD_ENVIRONMENT.md; output/T-008.1-server-discovery.log |
| Deployment architecture (§13.3) | PROPOSED | Docker Compose on the single VM (simplest fit; same compose file + a prod override). Images built and tested locally (same arch), shipped with `docker save | ssh docker load` (no registry needed). Pending: TLS decision (D-A), demo data (D-B) |
| Infrastructure provisioning (§13.4) | NOT NEEDED | VM, Docker, firewall already provided. Planned: /opt/esm-hub, fresh .env generated on the server (chmod 600) |
| Application build / images (§13.7) | READY (local) | 11 app images built (≈440 MB each, shared layers) + kafka/postgres/mailpit; 253 tests + E2E 6/6 green locally |
| Deployment (§13.7) | NOT STARTED | waiting on D-A, D-B |
| Database migrations / seed (§13.6) | READY | Flyway runs on start; demo seed only with profile `demo` (needs approval D-B) |
| Configuration and secrets (§13.4) | PLANNED | generate new DB password + JWT key pair on the server; never copy the dev .env |
| Security configuration (§13.5) | GAPS | (1) no domain → no valid TLS yet (D-A); (2) Mailpit publishes 8025 on 0.0.0.0 → bind to 127.0.0.1 in the prod override; (3) JVM memory limit 768 MiB tight (70–85% used) → raise; (4) Trivy image scan still pending |
| Health checks (§13.9) | NOT STARTED | external reachability of ports not tested (temporary-listener test was not permitted); will be verified on the real deployment |
| End-to-end tests on the deployed app (§13.9) | NOT STARTED | plan: smoke + Playwright 6 specs against the public URL, reboot test |
| CI/CD (§13.8) | NOT STARTED | |
| Deployment docs + handover (§13.11) | STARTED | CLOUD_ENVIRONMENT.md written |

Deployed version: none · Application URL: none (planned: http://92.5.154.198:8080 and/or https://… per D-A) · API docs URL: none

## Decisions (user, 2026-11-20)
- D-A → D-011: sslip.io hostname + Let's Encrypt (Caddy on 80/443); :8080 kept
- D-B → D-012: start empty (no demo seed in production)

## Finding from D-012 (dry run)
Without the demo seed there is no company, no user, no SLA policy and no catalogue item: nobody can log in. Reference data that admins can create via API: offices, departments, teams, categories, services. Needed: a one-time production bootstrap (company + first ADMIN from ESM_BOOTSTRAP_* secrets in the server .env, default P1–P4 SLA policies), idempotent and disabled once users exist.
Verification without demo data: run the Playwright suite against a temporary STAGING stack with the demo profile on port 8888 on the same VM (separate compose project, own volumes), then remove it; on production run read-only smoke checks + one bootstrap-admin login.

## Superseded options (kept for history)
- D-A HTTPS: no domain supplied. Options: free IP-based hostname (e.g. 92-5-154-198.sslip.io) + Let's Encrypt via a Caddy reverse proxy on 80/443 (valid TLS, §13.5), with :8080 kept for the judges' link; or plain HTTP on :8080 only (provider's example; violates §13.5 → record as accepted risk)
- D-B Demo data: load the synthetic demo seed (users, 150 incidents, …) on the server? Without it the app starts empty (§13.6 needs approval)

## Next deployment action
1. Build the production bootstrap (directory + incident services) with unit/IT tests
2. Prod override (mailpit 127.0.0.1, memory limits, TLS proxy if chosen) → Trivy scan → ship images → generate .env on server → compose up → verify (§13.9) → reboot test → docs + handover
