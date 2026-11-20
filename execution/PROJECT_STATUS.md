# Project Status
- **Overall:** COMPLETED by user decision (2026-11-20, D-013). Not deployed to the cloud; §13.13 completion criteria overridden by the user
- **Product:** esm-hub (products/esm-hub/source/esm-hub)
- **Stack:** Java 27 / Spring Boot 4.1 microservices + Kafka 4.4 + PostgreSQL 16 + React 19 (user-specified, D-006; R/docs/architecture/TECH_STACK.md). Technology Selection Checkpoint and Gate passed (compatibility spike T-002.2)
- **Current phase:** closed (stopped after Phase 5 local verification and the Phase 6 cloud dry run)
- **Completed phases:** 1 Discovery, 2 Design, 3 Planning, 4 Implementation
- **Pending phases:** none (closed). Outstanding, not performed by user decision: production bootstrap (company/first admin/SLA defaults), Trivy image scans, Mailpit 127.0.0.1 binding, JVM memory limits, cloud deployment + Caddy TLS + backups + post-deployment verification, CI/CD + Gradle dependency locking, docs/deployment set + runbooks, README/CONFLUENCE_PAGE.md/delivery report/packaging check; PO approvals BQ-1..10 and JDK 27→25 LTS still open
- **Progress:** verified locally: clean build 253 tests, frontend 18 tests, compose stack healthy, API smoke test, Playwright 6/6; cloud environment discovered + dry run passed
- **Major blockers:** none (closed)
- **Last updated:** 2026-11-20T11:49Z
