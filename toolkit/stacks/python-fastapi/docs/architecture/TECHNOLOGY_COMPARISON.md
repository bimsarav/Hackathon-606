# Sample App Technology Comparison

Record of the Technology Selection Checkpoint (MASTER_PROMPT §9.16). Write the options here **before** showing the menu, so they survive an interruption.

## 1. Options presented
TODO-PRODUCT: the numbered menu as shown to the user (2–5 options + "Let the AI Agent Decide"), one line each, with the profile name where an option came from `toolkit/stacks/`.

## 2. Evaluation (§9.16.5 criteria)
Score 1–5 (5 = best fit for this product). Critical criteria decide ties.

| Criterion | Priority | python-fastapi | TODO option 2 | TODO option 3 |
|---|---|---|---|---|
| Functional requirement suitability | Critical | TODO | | |
| Security | Critical | 3: strong validation and headers; auth must be added (ADR 0004) | | |
| Maintainability | Critical | 4: typed end to end; two toolchains | | |
| Architecture suitability | High | TODO | | |
| Performance | High | 4: ASGI, async available | | |
| Scalability | High | 4: stateless API and static SPA scale horizontally | | |
| Development productivity | High | 4: fast APIs; UI and auth are built by hand | | |
| Integration capabilities | High | 5: OpenAPI-first, Python ecosystem | | |
| Testing support | High | 5: TestClient + Testcontainers, Vitest | | |
| Long-term ecosystem support | High | 4: FastAPI is 0.x; React and SQLAlchemy mature | | |
| Deployment complexity | Medium | 4: api + web images + database | | |
| Infrastructure cost | Medium | 5 | | |

## 3. Decision
TODO-PRODUCT: selected option, who selected it (user number / text / autonomous), the key trade-offs accepted, and why the others were rejected (§9.18).
