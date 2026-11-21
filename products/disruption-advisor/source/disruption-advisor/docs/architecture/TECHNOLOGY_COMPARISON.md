# Disruption Advisor Technology Comparison

Record of the technology selection: the options considered, how they scored and why one was chosen.

## 1. Options considered
Options evaluated on 2026-11-20:
1. **Python FastAPI + React + DuckDB/Parquet + OR-Tools + Claude** (versions verified on 2026-11-20).
2. **Python Django + the same data/optimisation libraries**: server-rendered UI.
3. **Java Spring Boot + Timefold solver + React**: the organisation's other proven stack.

## 2. Evaluation
Score 1–5 (5 = best fit for this product). Critical criteria decide ties.

| Criterion | Priority | 1 Python FastAPI (+DuckDB, OR-Tools) | 2 Python Django | 3 Java Spring + Timefold |
|---|---|---|---|---|
| Functional requirement suitability | Critical | 5: Python has the strongest data (DuckDB, pyarrow) and optimisation (OR-Tools) libraries; rich interactive UI for what-if | 4: same libraries; server-rendered pages make interactive weight sliders and tables harder | 3: Timefold fits optimisation; data wrangling of the extracts is weaker on the JVM |
| Security | Critical | 3: strong validation and headers; auth added by hand (ADR 0004) | 4: built-in auth and admin | 4: Spring Security |
| Maintainability | Critical | 4: typed end to end; two toolchains | 4: one toolchain | 3: many modules; heavier for a small team |
| Architecture suitability | High | 5: API-first engine + SPA; engine reusable by later agents (phase 3) | 3: UI coupled to the server | 3: microservices are unjustified for this scope |
| Performance | High | 5: DuckDB in-memory queries, CP-SAT < 1 s | 4 | 4 |
| Scalability | High | 4: stateless API and static SPA scale horizontally | 4 | 5 |
| Development productivity | High | 4 | 4 | 3 |
| Integration capabilities | High | 5: OpenAPI-first; Anthropic Python SDK | 4 | 4 |
| Testing support | High | 5: TestClient + Testcontainers, Vitest, Playwright | 5 | 5 |
| Long-term ecosystem support | High | 4: FastAPI is 0.x; others mature | 5 | 5 |
| Deployment complexity | Medium | 4: api + web + db + one-shot ingest | 4 | 3 |
| Infrastructure cost | Medium | 5 | 5 | 3: larger memory footprint |

## 3. Decision
**Selected: option 1**, on 2026-11-20.
- **Why it wins:** it is the only option that is top-scoring on functional fit and architecture together. The Python data and optimisation ecosystem matches the problem (Parquet ingest, rules, CP-SAT), and the API-first engine can be reused by the phase-3 agent.
- **Trade-offs accepted:** two toolchains (Python + Node); authentication built by hand for the MVP (ADR 0004); FastAPI 0.x pinned to a minor version.
- **Why the others were rejected:**
  - Django: the server-rendered UI suits forms, not the interactive what-if analysis.
  - Java/Spring + Timefold: heavier, a weaker data-wrangling ecosystem, and microservices would be unjustified for one bounded problem.

Versions were verified on PyPI on 2026-11-20 (Python 3.14 wheels for every add-on): [COMPATIBILITY_MATRIX.md](COMPATIBILITY_MATRIX.md).
