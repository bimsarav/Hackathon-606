# RESUME (updated 2026-11-19T17:58Z) — session stopped by user (tokens exhausted)
Product: esm-hub (R = products/esm-hub/source/esm-hub) · Phase: 4 · Task: T-100
Last DONE: libs, directory-service (unit 5/5, IT 8/8, seed), gateway (2/2), Dockerfile, compose (validated), CI, ADRs, playbook, contracts
In progress (may be INTERRUPTED — background agents stop with the session):
  T-004.2 incident-service · T-004.3 request+change · T-004.4 asset+knowledge+audit · T-004.5 notification+reporting
Next on resume:
 1) For each service above: check R/services/<svc>/ files, then run
    ESM_GRADLE_PROJECT_CACHE=.gradle-<svc> R/scripts/build.sh :services:<svc>:build > /tmp/<svc>.log 2>&1; grep -E "FAILED|BUILD" /tmp/<svc>.log
    and check R/services/<svc>/src/main/resources/db/seed/V900__demo_seed.sql. Green + seed = done; otherwise relaunch a builder ONLY for the missing parts (briefs: scope per service in docs/architecture/architecture.md + docs/development/service-playbook.md + Python spec in ../backup-1training).
 2) Finalise gateway routes (R/services/gateway/src/main/resources/application.yml) to the real controller paths
 3) T-004.7 frontend (React) → web container in compose; 4) T-005 E2E/Playwright, Trivy; 5) T-007 docs, README, CONFLUENCE_PAGE.md
Running / last long command: none after exit; legacy DB container esmhub-legacy-db may still run (tools/seed/legacy-db.sh down to stop)
Environment: Gradle cache volume esmhub-gradle; image gradle:9.9.1-jdk27; build only via R/scripts/build.sh
Open questions / blockers: none (BQ-1..10 defaults pending PO)
Do NOT redo: libs, directory-service, seed tooling, gateway, compose, CI, ADRs, token review (execution/TOKEN_REDUCTION_REVIEW.md)
