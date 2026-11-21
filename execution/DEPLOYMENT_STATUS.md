# Deployment Status — disruption-advisor (MASTER_PROMPT §13.12, §14; phase gates per D-018)
Overall: **PHASES 1-3 AND 5 DEPLOYED – OPERATIONAL VERIFICATION PENDING** (no reboot test for phases 2, 3 and 5; nightly backups and HTTPS are phase 6) · Updated: 2026-11-21T05:35Z · production deploy of heshawa 2d58d6e verified: smoke 11/11, Playwright 8/8, new endpoints and reward plans checked (output/T-516-*.log); rollback tag pre-202611210525 + dump ~/backups/disruption-advisor/pre-202611210525.dump
Target: OCI VM 92.5.154.198 (same host as the esm-hub discovery below), port 8888, code ~/apps/disruption-advisor, extracts ~/disruption-advisor-input (700 + ACL for container uid 999), secrets ~/apps/disruption-advisor/settings.env (600; .env is a link to it). Demo logins: workspace input/secrets/disruption-advisor-demo-logins.txt (git-ignored).

| Phase | Status | Approval |
|---|---|---|
| 0 Design | DONE (artifact https://claude.ai/artifact/PTzSvCcSHABHNz7HYhxG2s) | user 2026-11-20 |
| 1 MVP | DEPLOYED (verified) | user 2026-11-20 ("define MVP … host it") |
| 2 Predict | DEPLOYED (verified; redeployed 2026-11-21T00:57Z, rollback tag pre-202611210055; reboot check skipped by user) (started 2026-11-20T23:25Z) | user 2026-11-21 ("start phase 2 now") |
| 3 Agent + what-if | DEPLOYED (verified 2026-11-21T02:32Z: smoke 11/11, e2e 6/6, AI agent run on prod; rollback pre-202611210231; reboot test not run) | user 2026-11-21 ("start phase 3") |
| 5 Passenger rewards + 7-day cascade check + tuned models | DEPLOYED (verified 2026-11-21T05:35Z: smoke 11/11, Playwright 8/8 incl. the cascade and reward tests, stages 3, 3b and 4 ran, reward plans via the trained model on a real delay and cancellation; rollback pre-202611210525; reboot test not run) | user 2026-11-21 ("deploy in production") |
| 4 Extend | NOT STARTED | needs approval |
| 6 Secure and protect (HTTPS + nightly backup, moved from phase 2 by user 2026-11-21) | NOT STARTED | needs approval |

| Area | Status | Evidence |
|---|---|---|
| Build (local) | DONE | check.sh PASS; Playwright 3/3 local; Trivy clean (SDK docstring false positive) — R/docs/testing/test-report.md |
| Images on server | DONE | built on server (api 1 GB, web 102 MB) — output/T-400.10-server-build.log |
| Data upload | DONE | 6 extracts, sha256 verified |
| Ingest on server | DONE | 15 min first run, same counts as local (27,879,509 bookings; 4,646 flights; 299,419 pax segments); fixed: input folder permission (ACL uid 999) |
| Packaging check | DONE | clean copy (git-ignore rules): no-cache build OK, README start-up OK on :18888, smoke 11/11, check.sh PASS (22+5), Trivy secret scan 0, no workspace references; temp stack removed |
| Health / smoke / E2E on server | DONE | api+web healthy; smoke 11/11 (output/T-400.10-smoke-server.log); Playwright 3/3 against http://92.5.154.198:8888 (output/T-400.10-e2e-server.log) |
| Reboot test (§14.5) | PASSED 2026-11-20 (user-authorised) | reboot 19:55:41Z, SSH back ~50 s, docker active, db/api/web healthy 30 s after boot unattended; 4 scenarios + 2 decisions intact; smoke 11/11 + Playwright 3/3 post-reboot (output/T-400.10-reboot-test.log, -smoke-post-reboot.log, -e2e-post-reboot.log) |

---
# (archived) esm-hub record
Overall: **NOT DEPLOYED — product closed by user decision 2026-11-20 (D-013)**. Discovery and dry run done; no deployment, no cloud verification, no application URL
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
