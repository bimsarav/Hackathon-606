# RESUME (updated 2026-11-19T22:00Z UTC) — T-200 stack-profile toolkit DONE; esm-hub T-100 resumes next
Product: esm-hub (R = products/esm-hub/source/esm-hub) · Phase: 4 · Task: T-100
Stack: Java 27/Spring Boot 4.1 microservices + Kafka + PostgreSQL 16 + React 19 — user-specified (PRODUCT_RULES §3, D-006) · R/docs/architecture/TECH_STACK.md
Last DONE: T-200 toolkit/ with verified profiles python-django + python-fastapi (D-007; outputs execution/logs/output/T-200-verify-*.log)
  New products: toolkit/stacks/README.md → scripts/check-stack-freshness.sh <p> → menu → scripts/new-product.sh <p> <name> (MASTER_PROMPT §9.16.0)
In progress (may be INTERRUPTED — background agents stopped with the 2026-11-19 session):
  T-004.2 incident-service · T-004.3 request+change · T-004.4 asset+knowledge+audit · T-004.5 notification+reporting
Next on resume:
 1) For each service above: check R/services/<svc>/ files, then run
    ESM_GRADLE_PROJECT_CACHE=.gradle-<svc> R/scripts/build.sh :services:<svc>:build > /tmp/<svc>.log 2>&1; grep -E "FAILED|BUILD" /tmp/<svc>.log
    and check R/services/<svc>/src/main/resources/db/seed/V900__demo_seed.sql. Green + seed = done; otherwise relaunch a builder ONLY for the missing parts (briefs: scope per service in docs/architecture/architecture.md + docs/development/service-playbook.md + Python spec in ../backup-1training).
 2) Finalise gateway routes (R/services/gateway/src/main/resources/application.yml) to the real controller paths
 3) T-004.7 frontend (React) → web container in compose; 4) T-005 E2E/Playwright, Trivy; 5) T-007 docs, README, CONFLUENCE_PAGE.md
 6) T-006.1: update esm-hub CI pins (checkout@v7.0.1, trivy-action@v0.36.0; toolkit/KNOWN_FACTS.md), enable Gradle dependency locking
Running / last long command: none. Docker volumes kept as build cache: sample-app-pycache, sample-app-devcache, trivy-cache, esmhub-gradle
Environment: Gradle cache volume esmhub-gradle; image gradle:9.9.1-jdk27; build only via R/scripts/build.sh. Disk ~93% full (32 GB free)
Open questions / blockers: BQ-1..10 defaults pending PO; JDK 27 (non-LTS) → 25 LTS pending PO
Do NOT redo: libs, directory-service, seed tooling, gateway, compose, CI, ADRs, token review, T-002.5..7 (rules + master prompt §9), T-200 (toolkit profiles)
