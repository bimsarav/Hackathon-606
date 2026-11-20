# RESUME (updated 2026-11-20T11:40Z) — cloud dry run done; waiting for user decisions D-A (HTTPS) and D-B (demo data)
Product: esm-hub (R = products/esm-hub/source/esm-hub) · Phase: 5 · Task: T-100 · Step: T-005.2 (partly done)
Last DONE (2026-11-20T08:34Z):
- Step 1: JWKS (!test profile) in asset/audit/knowledge/notification/reporting verified; smoke test of all API groups via :8080 OK -> execution/logs/output/T-005.2-smoke.log
- Step 2: Playwright E2E 6/6 passed (1.5 min) -> execution/logs/output/T-005.2-e2e-run3.log
  Fixes (tests only): nav clicks scoped to navigation 'Main' + exact names (4 specs); helpers.ts retries login on 429 (nginx login limit 5 r/min, burst 10, kept as a security control); playwright timeout 240 s
Facts: login body {email,password}; admin emily.jones9@example.test; audit API = AUDITOR/ADMIN only; all demo users Demo-Passw0rd1
Earlier DONE: clean full build 253 tests (T-005.1); frontend (lint, 18 tests, build); demo stack (compose) healthy
NEW RULE (2026-11-20T09:02Z): MASTER_PROMPT §13 cloud deployment is mandatory; esm-hub = DEPLOYMENT PENDING, BLOCKED on B-002 (no cloud access found on this machine). Cloud details will arrive in a folder inside input/ (maybe mid-build): check input/ at every resume/step change; ask again before deployment if missing. State: execution/DEPLOYMENT_STATUS.md
CLOUD: T-008.1 discovery DONE + dry run passed (see execution/DEPLOYMENT_STATUS.md). SSH: ssh -i input/cloud-environment/hackathon22_172.31.76.23 -o IdentitiesOnly=yes opc@92.5.154.198 (key git-ignored)
NEXT: after D-A/D-B → T-008.2 architecture → deploy → verify (see DEPLOYMENT_STATUS.md)
ALSO NEXT (only when the user asks; deferred by user 2026-11-20): rest of T-005.2 (package.sh, Trivy scans), T-006.1 CI/scripts/runbooks, T-007.1 README, docs, CONFLUENCE_PAGE.md, packaging check, then archive logs (scripts/archive-product-logs.sh esm-hub --status delivered --yes)
Running: docker compose stack (R) (esmhub-legacy-db container no longer exists, checked 2026-11-20)
E2E run cmd (from R/e2e): docker run --rm --network host --ipc=host -u $(id -u):$(id -g) -e HOME=/tmp -e E2E_BASE_URL=http://localhost:8080 -v "$PWD":/work -w /work mcr.microsoft.com/playwright:v1.49.1-noble npx playwright test
Environment: build only via R/scripts/build.sh; R/.env has generated secrets (git-ignored)
Do NOT redo: services, libs, frontend, full build, smoke test, E2E
