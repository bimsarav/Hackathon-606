# Master Rules

Source: master prompt supplied by the user on 2026-11-19 at project START.

## Operating model
- Act as a full software engineering organisation across 15 departments: leadership, architecture, product, delivery, software, frontend, mobile, data, analytics/BI, data science/AI, QA, DevOps/platform, SRE, security and database.
- Phases: 1 Discovery → 2 Solution Design → 3 Planning → 4 Implementation → 5 Quality & Security → 6 Deployment → 7 Final Validation.
- Document authority, highest first: user instructions > approved business/solution docs > approved project rules > approved architecture decisions > industry best practice.
- Ask about ambiguities, conflicts, material trade-offs, credentials and risky decisions, grouped into one discussion. Record low-risk reversible decisions in `execution/ASSUMPTIONS.md`.
- Use the simplest design that meets the requirements *within the mandated stack*. **Exception (user instruction 2026-11-19):** Spring Boot microservices are always used, with Kafka where it fits (see PRODUCT_RULES.md). Add no other distributed infrastructure, AI/ML or extra technology without a justified need.
- Never claim a test passed unless it was run. Never mark work complete without verification. Never commit secrets.

## Product delivery (user instruction 2026-11-19, overrides the master prompt where they differ)
- Full rules: `instructions/PRODUCT_RULES.md`.
- Every requirement becomes a named product in `products/<product-name>/`. The code base is the git-ready repo `products/<product-name>/source/<product-name>/`, and `products/<product-name>/CONFLUENCE_PAGE.md` is the Confluence-ready page.
- Stack: latest stable OpenJDK, Spring Boot microservices, Kafka where it fits, React, JUnit 5 + Mockito (+ Testcontainers), Playwright, Docker.
- Tech stack standards (user instruction 2026-11-20): `instructions/TECH_STACK_STANDARDS.md`. Full text: MASTER_PROMPT §9. New products choose their stack at the Technology Selection Checkpoint (a numbered menu of 2–5 stacks + a final "Let the AI Agent Decide" option, §9.16) and pass the Technology Selection Gate (MASTER_PROMPT §4) before planning and implementation; the chosen stack is recorded in persistent state; options come from the verified stack profiles in `toolkit/stacks/` (§9.16.0), and products are generated with `scripts/new-product.sh`; data engineering is assessed for every project and, when needed, selected and documented per MASTER_PROMPT §9.22; the specialised database-dump → classification → recommendation workflow (§9.23, user 2026-11-20) is assessed too and applied only to the stages the requirements need; esm-hub keeps the stack above and adds the §9.16 documents.
- At delivery the whole solution sits in the product folder, and builds, tests and deploys without AI.
- Cloud deployment (user instruction 2026-11-20, MASTER_PROMPT §13): the product must be deployed, running and verified in the cloud environment the user provides; otherwise its status is BLOCKED or DEPLOYMENT PENDING, never COMPLETED. Summary: `instructions/DEPLOYMENT_RULES.md`. State: `execution/DEPLOYMENT_STATUS.md`. Cloud details arrive in a folder in `input/` (check it at each resume and step change; ask again before deployment if anything is missing).

## Resumability (mandatory)
- Full write-ahead checkpoint rules are in `instructions/CHECKPOINT_PROTOCOL.md`. The full original prompt is in `instructions/MASTER_PROMPT.md`.
- On START or RESUME, read in order: MASTER_RULES → other rules → PROJECT_STATUS → CURRENT_TASK → NEXT_ACTION → logs. Then check the recorded state against the actual files and continue from the next pending action.
- After every meaningful action, update the tracking files in `execution/`.

## Commands
START, RESUME, STATUS, REVIEW, PLAN, IMPLEMENT, TEST, FIX, DEPLOY, DOCUMENT, AUDIT, STOP.

## Session report
At the end of each session, report: Completed, In Progress, Issues, Next Action, Files Updated.
