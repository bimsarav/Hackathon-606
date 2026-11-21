# Current Task
> **CLOSED 2026-11-20: esm-hub marked COMPLETED by user instruction (D-013).** Open `[ ]`/`[~]` items below were not performed and are not done.
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
- [x] T-005.1 full build (253 tests green) · [~] T-005.2 package + stack + Playwright E2E (stack + smoke + E2E 6/6 done; package + Trivy pending) · [ ] T-006.1 CI/scripts/runbooks · [ ] T-008 cloud deployment (MASTER_PROMPT §13; BLOCKED B-002; state execution/DEPLOYMENT_STATUS.md): T-008.1 discovery [x] · T-008.2 architecture + ADR · T-008.3a production bootstrap (company + first admin + SLA defaults) · T-008.3 infra/config/secrets + Caddy TLS · T-008.4 deploy · T-008.5 verify (§13.9, Playwright vs cloud URL) · T-008.6 docs/deployment + handover · [ ] T-007.1 (after T-008) delivery, README, CONFLUENCE_PAGE.md, packaging check
- [x] T-900 (sub-task) token-reduction review delivered by the background agent

## T-300 Airline domain research (user 2026-11-20, MASTER_PROMPT §15) — KB: documentation/knowledge-base/airline/ (= KB/)
- [x] T-300.0 §15 merged verbatim; DOMAIN_RESEARCH_RULES.md; KB skeleton; D-016
- [x] T-300.1 Disruption management first pass (5 parallel research agents; each writes its own file)
      files: [x] KB/topics/disruption-management/01-disruption-prediction.md [x] 02-network-impact-and-recovery.md [x] 03-passenger-impact.md [x] 04-passenger-prioritization-and-rights.md [x] 05-occ-pcu-workflows-and-systems.md
- [x] T-300.2 Synthesis: 00-OVERVIEW.md (14 §15.8 sections), SOURCES.md (merged registry), GLOSSARY.md, README topic map
- [ ] T-300.3 Next pass (on user direction): close overview §13 research gaps; validate airline-specific items with the target airline

## T-400 UC5 disruption-advisor (user approved design → MVP → host, 2026-11-20). R = products/disruption-advisor/source/disruption-advisor
- [x] T-400.0 Questions register (execution/QUESTIONS_UC5.md) · [x] T-400.1 inbox sort · [x] T-400.2 aircraft registry · [x] T-400.3 synthetic data
- [x] T-400.4 Generate product from python-fastapi profile; D-018..D-020
- [x] T-400.5 Design diagrams (artifact https://claude.ai/artifact/PTzSvCcSHABHNz7HYhxG2s) (R/docs/architecture/*.md, Mermaid) + view location to user
- [x] T-400.6 MVP definition + incremental deployment plan (R/docs/delivery/) 
- [x] T-400.7 Version verification of add-on libs (COMPATIBILITY_MATRIX)
- [x] T-400.8 MVP build
      files: [x] backend/app/ingest/convert.py (raw → typed Parquet) [x] backend/app/ingest/build.py (ops Parquet + synthetic enrichment) [x] app/data/airports.csv
             [x] app/engine/* [x] app/advisor.py + auth + models + alembic 0001 [x] backend tests (22 pass) [x] frontend [x] e2e (Playwright 3/3) [x] compose ingest service + limits + log rotation
- [x] T-400.9 Tests (pytest 22, vitest 5, Playwright 3; Trivy clean exc. SDK docstring false positive) · [x] T-400.10 Deploy MVP to OCI :8888 + verify + reboot test PASSED · [x] T-400.11 Close-out: arch docs (TECH_STACK, comparison, matrix, ADR 0001/0004-0007), CONFLUENCE_PAGE.md, DELIVERY_REPORT.md, packaging check PASS; Phase 2 NOT started (user)
> **PAUSED 2026-11-20T19:31Z by user** ("pause remaining steps until further notice"): T-400.10 reboot test and T-400.11 hand-over on hold.

> 2026-11-20T20:09Z: MVP close-out steps 1-6 DONE (user 'resume 1-6, do not proceed to phase 2'). Open: option override (not approved), commit + log archive (on user request), SSH key rotation (user).

## T-500 disruption-advisor Phase 2 "Predict" (approved by user 2026-11-21: "start phase 2 now"; Phase 3 needs separate approval)
Scope (R/docs/delivery/MVP_AND_INCREMENTAL_PLAN.md): delay-risk model (LightGBM, calibrated, SHAP reasons) · 7-day watchlist feeding Scenario A · per-passenger misconnect risk · (HTTPS + nightly backup moved to phase 6 by user 2026-11-21)
- [x] T-501 design update: phase 2 diagrams + ADR (model, features known 7 days ahead, time split) → tell user where to view
- [x] T-502 data study on history_flights (labels, features, baseline) → docs/testing/model-card.md
- [x] T-503 training stage (ingest stage 3 → /data/models), calibration, metrics vs baseline, unit tests
- [x] T-504 API: risk per flight, watchlist, misconnect risk per passenger; UI: watchlist page + risk chips; tests + e2e
- [-] T-505 HTTPS + backup: MOVED to phase 6 by user 2026-11-21 (needs separate approval; design ADR 0009)
- [x] T-506 deploy (prod phase 2 verified: smoke 11/11, e2e 4/4, risk API; reboot check skipped by user; docs done; NOT committed per user), verify (smoke, e2e, reboot check), docs (Confluence, README, methods PDF), report
