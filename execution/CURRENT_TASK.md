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
- [x] T-004.1 directory-service (reference) · [ ] T-004.2 incident · [ ] T-004.3 request + change · [ ] T-004.4 asset + knowledge · [ ] T-004.5 notification + audit + reporting
- [~] T-004.6 gateway, Dockerfile, compose · [ ] T-004.7 frontend
- [ ] T-005.1 full build + scans · [ ] T-005.2 Playwright E2E · [ ] T-006.1 CI/scripts/runbooks · [ ] T-007.1 delivery, README, CONFLUENCE_PAGE.md, packaging check
- [x] T-900 (sub-task) token-reduction review delivered by the background agent
