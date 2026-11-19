# Decisions
| ID | Decision | Type | Rationale | Approval |
|----|----------|------|-----------|----------|
| D-001 | Use the master-prompt directory structure under hack-isa/ | Process | Required by the user's master prompt | Approved (user instruction) |
| D-002 | Product delivery rules: products/<product-name>/ with CONFLUENCE_PAGE.md and the git-ready repo at source/<product-name>/; the whole solution moves there at delivery | Process | User instruction 2026-11-19 (layout option chosen by the user) | Approved (user instruction) |
| D-003 | Mandated stack: latest stable OpenJDK, Spring Boot microservices (always), Kafka where it fits, React, JUnit 5 + Mockito, Playwright, Docker. Overrides the master prompt's "avoid microservices" rule | Architecture | User instruction 2026-11-19 | Approved (user instruction) |
| D-004 | Previous Python/FastAPI ESMP solution removed: no longer needed because the stack changed | Process | User instruction 2026-11-19 | Approved (user instruction) |
