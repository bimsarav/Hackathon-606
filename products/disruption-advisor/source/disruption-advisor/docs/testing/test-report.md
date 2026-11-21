# Test Report

All results come from real runs: phase 1 (MVP) on 2026-11-20, phase 2 (Predict) on 2026-11-21 ([below](#phase-2-predict-2026-11-21)), phase 3 (Agent and what-if) on 2026-11-21 ([below](#phase-3-agent-and-what-if-2026-11-21)). Commands are in the README. Logs are in `logs/` and are not committed.

# Phase 1 (MVP)

## Local quality gate: `scripts/check.sh`
| Step | Result |
|---|---|
| Backend lint (Ruff, incl. security rules `S`) | PASS. `S608` is excepted for `app/engine/store.py` and `app/ingest/*`, where SQL interpolates only constant names and configured paths; user values are bound parameters (see `pyproject.toml`) |
| Backend format, mypy strict | PASS |
| Backend tests (pytest + Testcontainers PostgreSQL 18, Alembic) | **29 passed** (2026-11-21 bug-fix release); coverage 78% (the ingest is exercised by the real-data run below, not by unit tests) |
| Frontend type check (`tsc` strict), unit tests (Vitest), production build | PASS: **5 tests** |

The engine tests use a hand-made network (`backend/tests/ops_fixture.py`) and cover:
- delay propagation through turn times, and slack absorbing the delay;
- a same-type swap that removes the knock-on delay, and rejection of an infeasible swap;
- the option ranking;
- misconnects against the hub MCT table;
- cancellation: tier order, families kept together, non-revenue passengers last, an OPTIMAL seat assignment, and weights that never cross tiers;
- the EU261 bands;
- loading the store.

The API tests cover:
- authentication: wrong password, missing or forged token;
- both scenarios end to end;
- what-if weights, decisions (audit), message drafts;
- validation errors (RFC 9457) and 404s;
- that migrations match the models.

## Real-data run (local Docker Compose, then the server)
- **Ingest** (in the container), with the result also recorded in `ops/ingest_report.json`:
  - 27,879,509 booking rows converted to Parquet; 2 malformed lines rejected; 1 truncated inventory line skipped.
  - Built: 4,646 flights, 299,419 passenger segments in the window, 174,723 customer profiles.
- **Scenario A, G9519 DAC→SHJ, +150 min:**

  | Option | Delay | Legs | Missed connections | Cost |
  |---|---|---|---|---|
  | Absorb the delay | 480 min | 5 | 90 | AED 222,600 |
  | Swap in A6-ARI (recommended) | 150 min | 1 | 33 | AED 70,875 |

  Of the 33 passengers who still miss a connection, 31 are rebooked within 24 h. The explanation was written by `claude-opus-5-5` from the engine's figures; the request took about 4 s through nginx.
- **Scenario B, cancellation G9562 SHJ→LYP:** 147 passengers and 60 free seats on the alternatives. CP-SAT solved it OPTIMAL in under 1 s: 60 passengers protected by tier and score, 87 offered next day with hotel.

## End-to-end: `scripts/e2e.sh` (Playwright 1.65.1, Chromium)
| Target | Result |
|---|---|
| Local stack `http://localhost:8888` | **3 passed**: wrong password rejected, and the API needs a token; scenario A assessed, options compared and the recommendation approved; scenario B tier order, what-if re-run, message draft and plan approved |
| Server `http://<server>:8888` | **3 passed** before and after the reboot test; smoke test 11/11 (see `docs/deployment/DEPLOYMENT_GUIDE.md`) |

## Security scans (Trivy 0.76.2, HIGH/CRITICAL)
| Target | Result |
|---|---|
| Repository: `uv.lock`, `package-lock.json`, Dockerfiles (dependencies, secrets, misconfiguration) | 0 findings |
| Image `disruption-advisor-web` | 0 findings |
| Image `disruption-advisor-api` | 0 vulnerabilities. The secret-rule matches (`gcp-service-account`) are **false positives** in the Anthropic SDK's own docstrings (the text `"type": "service_account"` in `anthropic/resources/beta/agents/*.py`); no credential is present |

# Phase 2 (Predict), 2026-11-21

## Local quality gate: `scripts/check.sh`
| Step | Result |
|---|---|
| Backend lint, format, mypy strict | PASS |
| Backend tests (pytest + Testcontainers PostgreSQL 18) | **47 passed** |
| Frontend type check, unit tests (Vitest), production build | PASS: **9 tests** |

New tests in this phase:
- `backend/tests/test_delay_risk.py`:
  - the delay curve interpolates between thresholds;
  - AUC and Brier match textbook values;
  - the planning delay is exceeded with a 20% chance;
  - the miss probability grows as the slack shrinks, and a late onward flight saves some connections;
  - the model learns a pattern planted in the test network and writes `flight_risk`, `connection_risk` and the model card;
  - training is deterministic (same data, same output);
  - the watchlist and flight-risk API (sign-in required).
- `frontend/src/App.test.tsx`: the watchlist lists flights at risk, opens one with reasons and connections and starts a scenario; it shows the API error when the risk data is not available.
- `frontend/src/RotationBoard.test.tsx` (teammate addition): legs sit on the scheduled aircraft before and on the operating aircraft after; both boards render with a summary of the change.

## Model evaluation (time-ordered)
Evaluation model trained on 2026-01-01 .. 2026-10-21 (57,104 flights), tested on 2026-10-21 .. 2026-11-18 (5,956 flights), production run on the server:

| Delay of at least | Model AUC | Route × hour baseline AUC |
|---|---|---|
| 15 min | 0.798 | 0.741 |
| 60 min | 0.757 | 0.676 |

Missed-connection backtest (SHJ connections in the test weeks, no-slack band): 0.70 predicted vs 0.69 observed. Method, calibration decision and limitations: [model-card.md](model-card.md).

## Server checks (`http://<server>:8888`)
| Check | Result |
|---|---|
| Smoke test `scripts/smoke.sh` | **11/11** |
| Playwright `scripts/e2e.sh` (Chromium) | **4 passed**: wrong password and token check; scenario A; scenario B; phase 2 watchlist (ranks flights, shows reasons, opens a delay scenario) |
| Risk API | Watchlist 1,491 flights in 7 days: 18 high, 140 medium risk; model card served |
| Reboot test | **Not done** (skipped by user decision) |

The local Playwright run was not done: the development machine's bookings Parquet still uses the old `dep_year` layout. The runtime code is identical to the server, so the end-to-end tests ran against the server. No Trivy scan is recorded for the phase 2 images.

# Phase 3 (Agent and what-if), 2026-11-21

## Local quality gate: `scripts/check.sh`
| Step | Result |
|---|---|
| Backend lint, format, mypy strict | PASS |
| Backend tests (pytest + Testcontainers PostgreSQL 18) | **69 passed** |
| Frontend type check, unit tests (Vitest), production build | PASS: **19 tests** |

New tests in this phase:
- `backend/tests/test_strategies.py` (10 tests, on the hand-made network with a round trip and its passengers):
  - cancelling a round trip stops the delay spreading; no pair is offered when the delay never reaches it;
  - a round trip is labelled "Consolidate" when every passenger fits on same-route flights;
  - every option has passenger KPIs;
  - each strategy picks its best option; switching the strategy changes the recommendation, not the numbers;
  - selecting the cancel option lists its cancelled passengers; an unknown strategy is rejected;
  - ties are broken by option key; at equal cost, keeping the schedule beats cancelling.
- `backend/tests/test_agent.py` (10 tests, with a scripted fake Claude client):
  - tool schemas are strict and use only supported keywords;
  - the AI loop recommends an engine option with a trace, and sends the expected request settings;
  - **privacy:** every request sent to the AI service is checked against all PNRs, customer keys, passenger IDs and (synthetic) passport numbers in the fixture; none appear;
  - an option the engine did not produce is refused, and the model can correct it;
  - without an API key the planner recommends the strategy's pick, using the predicted delay when none is given;
  - a refusal and the step limit fall back to the planner and keep the AI's steps;
  - tool inputs are validated;
  - the runs API saves a scenario for approval, and validates its input.
- `frontend/src/Phase3.test.tsx` (9 tests): the strategy panel shows three picks and switches on the server; the new pick is marked recommended; passengers are labelled by why they need a new flight; a scenario made by the agent shows its recommendation; the run view shows steps live, then the recommendation and the open-scenario button; it says when the planner answered; a failed run shows its error and retries with the same inputs; a run already in progress is explained; the watchlist passes the flight and its planning delay.
- `e2e/tests/advisor.spec.ts`, two new Playwright tests:
  - "phase 3: strategies switch the recommendation";
  - "phase 3: the agent investigates a flight and its recommendation opens for approval" (accepts the AI or the planner as source).

## Real-data checks before the deploy (server data, read-only container)
- **Delay scenarios with the new options:** 0.6–7 s per scenario.
- **Live agent probe, real API:** G9519 with no delay given; the agent used the 56-minute planning delay, made 7 tool calls in 37 s and recommended `swap:A6-ANO` under "protect passengers". Details: [agent-card.md](agent-card.md).

## Server checks (`http://<server>:8888`)
| Check | Result |
|---|---|
| Deployment | 2026-11-21 02:31 UTC, rollback tags and database dump taken first, Alembic 0002 applied |
| Smoke test `scripts/smoke.sh` | **11/11** |
| Playwright `scripts/e2e.sh` (Chromium) | **6 passed**: the four earlier tests plus the two phase 3 tests |
| Agent run during the Playwright test | G9901_202611220500: source `ai:claude-opus-5-5`, 7 steps, 25 s, recommended `swap:A6-AOH` under "protect passengers" |
| Reboot test | **Not run** for phase 3 |

The e2e folder's `tsconfig.json` needs `@types/node` in the e2e `devDependencies` for a standalone `tsc` check; this predates phase 3 and does not affect the Playwright run. No Trivy scan is recorded for the phase 3 images.

## Phase 5, the 7-day tab and the model tuning (21 Nov 2026)

### What was added
| Test file | Tests | What it checks |
|---|---|---|
| `backend/tests/test_rewards.py` | 17 (20 runs: the budget test has four budgets) | severity grows with delay, connection, wait and vulnerability; proxy preferences follow the booking clues; eligibility; a zero budget gives nothing and a large one the full plan; the plan never exceeds the budget and its spend matches its rows; a tighter budget never rewards more and keeps the most affected; non-revenue passengers are excluded; **a reward never repeats what the care plan gives**; the synthetic history is deterministic and labelled; the model beats both baselines on held-out passengers and learns who takes which reward; the plan uses the model; ingest stage 4 on the small fixture writes a labelled model and history; the **reward API** stays within the budget, never repeats care, validates input and needs a sign-in, and an approval goes to the audit log |
| `backend/tests/test_rewards.py` (upcoming segments and tiers) | +6 | connection vs return vs later travel; a cancellation hurts more when a connection or return is booked (and a delay does not change for the booking alone); flights coming up raise the voucher, miles, ticket and lounge preferences; the plan's severity ranks connection above return above none; a family account lifts the loyalty tier the reward models see; the API reports each passenger's upcoming flights |
| `backend/tests/test_cascade_check.py` | 3 | the formula and the six figures on a hand-made history (cascade pair, no pair when the buffer absorbs it, over-estimate, extreme outlier listed apart, different-station repositioning is not a pair); pairs older than a month are left out; the **cascade API** serves a consistent check and needs a sign-in |
| `backend/tests/test_delay_risk.py` | 9 | includes the last-week replay (kept; the panel was removed from the UI) |
| `frontend/src/App.test.tsx` | 11 | the reward table (passenger, reward, value; the rest under "More data"); the two-tab passenger panel; the cascade panel (six boxes, full view with both charts, outlier note, filter, Escape closes) |
| `e2e/tests/advisor.spec.ts` | 8 | adds: the 7-day tab shows the cascade panel and its full view instead of the launcher; a budget gives a reward plan from the preference model and the plan can be approved |

### Results
| Check | Result |
|---|---|
| Backend, without Docker | **73 passed**; 26 more need the PostgreSQL container (21 earlier tests plus the 5 new API tests) |
| The 5 new API tests and the existing API tests, on SQLite in a scratch copy | all passed except the Alembic migrations check, which needs PostgreSQL |
| Backend lint, format, strict types | clean |
| Frontend type check, unit tests, production build | clean, **24 passed**, built |
| Local stack on the merged tree (bundled PostgreSQL, Vite) | all four ingest stages ran (3, 3b, 4 and the rest); every GET endpoint 200; delay and cancellation scenarios created; reward plans computed and approved (201); every frontend module compiles in the dev server |
| Negative budget on the local stack | 500, because the local run uses Python 3.12 and `HTTPStatus.UNPROCESSABLE_CONTENT` needs 3.13+; the server (Python 3.14) returned 422 on the same request |

### Model results
- Delay model tuning and comparison (nine candidates): [model-selection.md](model-selection.md), including the check of the teammates' `month` and `route_freq` features.
- Reward preference model (eight candidates, grouped folds, oracle bound): [reward-model-selection.md](reward-model-selection.md) and [reward-model-card.md](reward-model-card.md). The outcomes are simulated.

### Production check (2026-11-21 05:35 UTC, heshawa `2d58d6e`)
| Check | Result |
|---|---|
| Deployment | rollback tag `pre-202611210525` and a database dump first; all four ingest stages ran (stage 3 AUC-60 0.770, stage 3b 1,656 pairs, stage 4 AUC 0.702) |
| Smoke test `scripts/smoke.sh` | **11/11** |
| Playwright `scripts/e2e.sh` (Chromium) | **8 passed**, including the 7-day cascade panel with its full view and the reward plan with its approval |
| New endpoints | cascade 200; reward plans via the trained model on a real cancellation and delay of G9148 (215 passengers): severity with a connection 75.9 against 65.0 without (cancellation); an approval is recorded (201); a negative budget returns 422; no sign-in returns 401 |
| Reboot test | **Not run** for this release |
| Found while deploying | the server held a `nginx.conf` fix that was not in git (committed first), and a stale source file broke the first web build (removed; see the deployment guide) |

### Not run
The new Playwright tests have not been run locally (no Playwright or Docker on this machine) and not on the server since the fix. The 26 PostgreSQL-backed tests ran only in the SQLite scratch copy.
