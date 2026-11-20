# Current Task
- **ID:** T-100 esm-hub product build (user 2026-11-19: "create the solution product")
- **Objective:** Deliver esm-hub (ESMP): Spring Boot microservices + Kafka + React, Gradle, JUnit/Mockito/Testcontainers/Playwright, Docker, git-ready, Confluence page
- **Repo:** products/esm-hub/source/esm-hub/ (= `R/`)
- **Parallel sub-task (this run only):** background agent → execution/TOKEN_REDUCTION_REVIEW.md
- **Outstanding:** BQ-1..10 defaults pending PO approval

## Steps (`[ ]` todo · `[~]` started · `[x]` done and verified)
- [x] T-001.1 Sort inbox · [x] T-001.2 Sensitivity · [x] T-001.3 Name + scaffold
- [x] T-001.4 R/docs analysis docs (copied from ../backup-1training; adapt stack refs)
- [x] T-002.1 R/docs/architecture/architecture.md
- [x] T-002.2 Gradle foundation + JDK 27 spike: settings, catalog, buildSrc, wrapper, libs/esm-common, libs/esm-test-support, libs/esm-directory-replica, scripts/build.sh
      files: all done (libs: esm-common 33 classes, esm-test-support, esm-directory-replica)
- [x] T-002.3 tools/seed generator → per-service demo seed SQL
- [x] T-002.4 ADRs
- [x] T-002.5 Tech stack standards (user 2026-11-20): instructions saved; R/docs/architecture/TECH_STACK.md, TECHNOLOGY_COMPARISON.md, COMPATIBILITY_MATRIX.md
- [x] T-002.6 MASTER_PROMPT consolidated with §9 tech stack standards (user 2026-11-20)
- [x] T-201 MASTER_PROMPT §9.22 data engineering standards + esm-hub DE assessment (user 2026-11-20)
- [x] T-200 Stack-profile toolkit (user 2026-11-20): python-django + python-fastapi VERIFIED (execution/logs/output/T-200-verify-*.log), scripts, rules
- [x] T-002.7 MASTER_PROMPT: stack selection menu workflow merged into §9.16 (user 2026-11-20)
- [x] T-004.1 directory-service (reference) 
- [x] T-004.2..5 services (agents; verified by T-005.1) · [x] T-004.6 gateway, Dockerfile, compose (stack healthy) · [x] T-004.7 frontend
- [x] T-005.1 full build (253 tests green) · [~] T-005.2 package + stack + Playwright E2E (stack + smoke + E2E 6/6 done; package + Trivy pending) · [ ] T-006.1 CI/scripts/runbooks · [ ] T-007.1 delivery, README, CONFLUENCE_PAGE.md, packaging check
- [x] T-900 (sub-task) token-reduction review delivered by the background agent
