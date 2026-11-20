# RESUME (updated 2026-11-20T14:53Z) — esm-hub CLOSED: marked COMPLETED by user decision (D-013)
Product: esm-hub (R = products/esm-hub/source/esm-hub) · Status: COMPLETED by user instruction, NOT deployed
Verified locally: clean build 253 tests; frontend lint + 18 tests; compose stack healthy; API smoke (output/T-005.2-smoke.log); Playwright 6/6 (output/T-005.2-e2e-run3.log)
Cloud: OCI VM discovered + read-only dry run passed (R/docs/deployment/CLOUD_ENVIRONMENT.md, execution/DEPLOYMENT_STATUS.md); nothing deployed
Not performed (user 2026-11-20): not performed by user decision: production bootstrap (company/first admin/SLA defaults), Trivy image scans, Mailpit 127.0.0.1 binding, JVM memory limits, cloud deployment + Caddy TLS + backups + post-deployment verification, CI/CD + Gradle dependency locking, docs/deployment set + runbooks, README/CONFLUENCE_PAGE.md/delivery report/packaging check; PO approvals BQ-1..10 and JDK 27→25 LTS still open
Running: local docker compose stack (R) still up
Pending housekeeping (needs user go-ahead): final commit of the product, then scripts/archive-product-logs.sh esm-hub --status delivered --yes (moves logs to execution/archive/, resets tracking files)
Workspace rules: MASTER_PROMPT §13 cloud, §14 server ops (D-014), §9.24 product vs AI agent stack (D-015, instructions/AGENT_TECH_STACK.md) merged 2026-11-20
