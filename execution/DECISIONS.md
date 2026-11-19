# Decisions (this product run)
Standing workspace rules (folder layout, mandated stack, logging) live in `instructions/` and are not repeated here.
| ID | Decision | Type | Rationale | Approval |
|----|----------|------|-----------|----------|
| D-001 | Product name **esm-hub** (Enterprise Service Management Hub) | Business | The requirement is the ESMP pack in input/inbox; short, descriptive, kebab-case | Accepted |
| D-002 | Run all phases autonomously; open business rules BQ-1..10 use configurable defaults marked pending PO approval | Process | User: "create the solution product" | Accepted (rules pending PO) |
| D-003 | Versions: OpenJDK **27** (27.0.1), **Gradle 9.9.1** (gradle:9.9.1-jdk27), Spring Boot 4.1.2, Spring Cloud 2025.1.4, springdoc 3.2.0, Kafka 4.4.0 (KRaft), Testcontainers 2.0.5, React 19.3, Playwright 1.65, PostgreSQL 16 (all checked 2026-11-19) | Technical | PRODUCT_RULES §3, TECHNICAL_RULES | Accepted (verified by the spike) |
| D-004 | Temporary sub-task (this run only): parallel analysis of token-reduction options → execution/TOKEN_REDUCTION_REVIEW.md | Process | User instruction | Accepted |
