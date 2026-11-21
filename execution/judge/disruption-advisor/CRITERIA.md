# Judging criteria: disruption-advisor (aeroRecovery)

Created 2026-11-21. Derived from the product's own specification (JUDGE_RULES §2):
- `input/requirements/Disruption_Management_UC5.docx`: UC5 challenges 1–4, AI-driven prioritisation, expected solution (§5), example scenario (§6), final deliverables (§8).
- `input/inbox/client presentation.png`: ISA Hackathon 606 judging weights.
- `input/inbox/submission.png`: required submission package.
- Product decisions in force: ADR 0015 (UI 8080, API 8888, HTTP), roles (OCC and Evaluator distinct; PCU = OCC), PRODUCT_RULES §7 (no build-process traces).

## 1. Score categories (client weights replace the §16.4 defaults)
| # | Category (client) | Weight | What the Judge checks | §16.4 lens used |
|---|---|---:|---|---|
| 1 | Problem significance & fit | 20 | Addresses UC5 and creates ISA/airline business value: every UC5 challenge and acceptance criterion (Challenge 1 predictive, 2 flight recovery, 3 passenger recovery, prioritisation list, 4 decision support), the §6 example scenario questions, business benefits | Business requirements & functional completeness; Overall business value & practicality |
| 2 | Execution | 25 | Works end-to-end on the provided environment: deployed and reachable on the VM (UI :8080, API :8888), real data, both scenarios, approvals, prediction, rewards, agent, evaluator mode; tests run and pass; restart and recovery behaviour | DevOps, deployment & operations; Testing & QA; Performance, scalability & reliability |
| 3 | Technical depth | 20 | Sound architecture, design and integration; quality over tool count: engine design, data pipeline (Parquet/DuckDB), CP-SAT, ML models and their validation, agent design, code quality, maintainability | Architecture & system design; Code quality & engineering standards; Maintainability & extensibility |
| 4 | Novelty | 15 | Original approach, not a thin wrapper: own engine, optimiser, models; AI used where it adds value | Overall business value; Architecture |
| 5 | Responsible design | 10 | Privacy, guardrails, errors, hallucinations and cost: no personal data to the AI, engine-grounded numbers, fallbacks, recommend-only with audit, cost caps, security posture (TLS, rate limits, exposed ports, secrets) | Security & compliance |
| 6 | Clarity | 10 | Effective pitch, demo and documentation: slides, README, architecture docs and diagrams, Confluence, user guide; accuracy and consistency of docs with the running system | Documentation & diagrams |
| | **Total** | **100** | | |

## 2. Mandatory acceptance rules (a failure caps the verdict at REWORK REQUIRED)
1. The working demo is deployed and reachable on the provided VM, and its URL is stated (submission item 05).
2. The submission package exists and meets its limits: solution design PDF (01); source ZIP with README, setup, dependencies and limitations (02); demo video MP4 up to 10 minutes (03); presentation slides PDF **up to 10 pages** (04); working demo link (05).
3. Every UC5 acceptance criterion in challenges 1–4 and the prioritisation list is met or explicitly declared out of scope with a reason.
3a. The UC5 §5 expected-solution items are met (disruption identification, impact analysis, intelligent passenger prioritisation, recovery recommendations, AI-powered insights, interactive demonstration), and the UC5 §8 final deliverables are met: a working AI-powered prototype; a live demonstration with the provided data and at least one disruption scenario; a demonstration of weighted passenger prioritisation; an explanation of the AI techniques and their contribution; a summary of business benefits and implementation considerations.
3b. Scope from the briefing (`input/requirements/UC5_briefing_transcript.txt`): one or two realistic disruption scenarios shown end to end (impact, available recovery, recommended action). Product-owner answers in `input/requirements/UC5_QnA_2026-11-20.txt` apply (e.g. inventory mismatches must not break the process).
4. The automated quality gate (`scripts/check.sh`) passes on the delivered commit, and post-deployment checks (smoke, Playwright) pass on the server.
5. No client deliverable contains build-process traces (PRODUCT_RULES §7).
6. A manual QA cycle through the UI of the deployed system (MASTER_PROMPT §17, `instructions/QA_RULES.md`) covers the delivered features of the release for each role (OCC, Evaluator), with evidence, and no open Critical or High QA defect remains (or the user has accepted it). The Judge assesses the QA evidence; a QA PASS alone is not proof.

## 3. Critical-failure rules (block approval regardless of score, §16.6)
- Personal data (names, booking references, document numbers, contact details) sent to the external AI service, or present in the Git repository or Confluence.
- Passenger prioritisation that lets commercial scores override passenger rights, mandatory assistance or operational requirements (UC5: "Respect passenger rights, mandatory assistance and operational requirements independently of commercial scores").
- Secrets in the repository, Confluence or client documents.
- A recommendation that can change airline data without human approval, or numbers shown to users that do not come from the engine.
- The deployed system unreachable, or its documented address wrong.
- Documentation that misstates how the system works in a way that could mislead a user or operator (for example ports, roles, security posture).

## 4. Change history
| Date | Change |
|---|---|
| 2026-11-21 | Created from UC5, the hackathon judging weights and the submission package. |
| 2026-11-22 | Mandatory rule 6 added: manual QA cycle through the UI (user instruction 2026-11-22, MASTER_PROMPT §17). |
| 2026-11-21 | Added UC5 §5 expected solution and §8 deliverables (3a), briefing scope and product-owner Q&A (3b), and the passenger-rights critical rule (Judge finding J-WR-008 on the first criteria review). |
