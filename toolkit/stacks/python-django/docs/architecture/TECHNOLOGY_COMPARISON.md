# Sample App Technology Comparison

Record of the Technology Selection Checkpoint (MASTER_PROMPT §9.16). Write the options here **before** showing the menu, so they survive an interruption.

## 1. Options presented
TODO-PRODUCT: the numbered menu as shown to the user (2–5 options + "Let the AI Agent Decide"), one line each, with the profile name where an option came from `toolkit/stacks/`.

## 2. Evaluation (§9.16.5 criteria)
Score 1–5 (5 = best fit for this product). Critical criteria decide ties.

| Criterion | Priority | python-django | TODO option 2 | TODO option 3 |
|---|---|---|---|---|
| Functional requirement suitability | Critical | TODO | | |
| Security | Critical | 4: built-in auth, CSRF, password hashing, deploy checks | | |
| Maintainability | Critical | 5: LTS line, one runtime, strict typing | | |
| Architecture suitability | High | TODO | | |
| Performance | High | 3: sync WSGI; fine for typical business load | | |
| Scalability | High | 3: horizontal app containers + PostgreSQL | | |
| Development productivity | High | 5: admin, forms, ORM, auth included | | |
| Integration capabilities | High | 4: DRF + OpenAPI | | |
| Testing support | High | 5: pytest-django + Testcontainers | | |
| Long-term ecosystem support | High | 5 | | |
| Deployment complexity | Medium | 5: one image + database | | |
| Infrastructure cost | Medium | 5 | | |

## 3. Decision
TODO-PRODUCT: selected option, who selected it (user number / text / autonomous), the key trade-offs accepted, and why the others were rejected (§9.18).
