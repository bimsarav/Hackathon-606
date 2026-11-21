# Delivery Report

Phase 1 (MVP): 20 Nov 2026, **deployed and verified**. Phase 2 (Predict): 21 Nov 2026, **deployed and verified; reboot check skipped by decision** (see [Phase 2](#phase-2-predict)). Phase 3 (Agent and what-if): 21 Nov 2026, **deployed and verified; reboot test not run** (see [Phase 3](#phase-3-agent-and-what-if)).

## Phase 1 (MVP)

### What was delivered
- **Application:** Disruption Advisor MVP, running on the provided OCI server at `http://<server>:8888`. Scenario A (delay impact and recovery options), scenario B (cancellation with seat-limited re-accommodation), priority weights with what-if, explanations and message drafts, approvals with an audit trail, and two demo roles.
- **Code:** this repository. Backend (FastAPI engine, ingest, API), frontend (React), Compose stack, tests (pytest, Vitest, Playwright), scripts (`check.sh`, `e2e.sh`, `smoke.sh`).
- **Documentation:**
  - architecture and diagrams (`docs/architecture/`);
  - ADRs 0001–0007;
  - compatibility matrix;
  - MVP and phase plan;
  - deployment guide;
  - test report;
  - methods PDF (`docs/delivery/Disruption_Advisor_Methods.pdf`);
  - Confluence page (product folder).

### Verification
| Check | Result | Evidence |
|---|---|---|
| Quality gate (`scripts/check.sh`) | Pass: 22 backend, 5 frontend tests, lint, strict types, build | `docs/testing/test-report.md` |
| Security scan (Trivy) | 0 HIGH/CRITICAL vulnerabilities; SDK docstring secret-rule hits are false positives | test report |
| Server deployment | `db`, `api`, `web` healthy; ingest of 27.9M bookings in 15 min | deployment guide |
| Smoke test on the server | 11/11, before and after the reboot | deployment guide |
| Playwright on the server | 3/3, before and after the reboot | deployment guide |
| Reboot test | Passed: back in ~50 s, healthy with no manual action, data intact | deployment guide |

### Known limitations
See the Confluence page and `docs/deployment/DEPLOYMENT_GUIDE.md`:
- synthetic loyalty, fare-family and special-service data;
- assumed costs and rules;
- no crew checks;
- capacity inferred for most flights;
- override of the recommendation not yet possible;
- HTTP only.

### Next steps (each needs approval)
- **Option override:** proposed.
- **Phase 2:** prediction (delivered 21 Nov 2026, below). HTTPS and backups moved to phase 6.
- **Phase 3:** AI agent and what-if.
- **Phase 4:** extensions.
- **Security housekeeping:** the server SSH key that was committed to the project's working repository should be replaced (server access, not part of this codebase).

## Phase 2 (Predict)
Date: 21 Nov 2026 · Approved on 21 Nov 2026 · Status: **deployed and verified on `http://<server>:8888`; reboot check skipped by decision (21 Nov 2026)**

### What was delivered
- **Delay-risk model** (`backend/app/ml/delay_risk.py`): LightGBM, one classifier per delay threshold (5–180 min), recency-weighted, features known 7 days ahead, TreeSHAP reasons in plain words, an arrival-delay curve and a missed-connection probability per connecting passenger. It runs as ingest stage 3 and retrains on every data load. Details: [model card](../testing/model-card.md).
- **API** (`backend/app/risk.py`, read-only, sign-in required): `GET /api/v1/risk/watchlist`, `/api/v1/risk/flights/{flight_id}`, `/api/v1/risk/model`.
- **UI:** "Delay watchlist (7 days)" tab with risk filter and sort; a flight opens its reasons and the connecting passengers at risk; "Analyse a N min delay" opens Scenario A with the planning delay. Teammate addition in the same release: a before/after aircraft rotation board in the delay view (`frontend/src/RotationBoard.tsx`).
- **Documentation:** SYSTEM_ARCHITECTURE §10, ADR 0008 (delay-risk model), ADR 0009 (HTTPS and backups, deferred to phase 6), model card, this report, test report, deployment guide, methods PDF, Confluence page.

### Verification
| Check | Result | Evidence |
|---|---|---|
| Quality gate (`scripts/check.sh`) | Pass: 47 backend, 9 frontend tests, lint, strict types, build | docs/testing/test-report.md |
| Server code | Server tree identical to the verified local tree (86 files, SHA-256) | docs/testing/test-report.md |
| Smoke test on the server | 11/11 | docs/testing/test-report.md |
| Playwright on the server | 4/4, including the new watchlist test | docs/testing/test-report.md |
| Risk API on the server | Watchlist: 1,491 flights in 7 days, 18 high and 140 medium risk. Model card: train 2026-01-01 .. 2026-10-21 (57,104 flights), test 2026-10-21 .. 2026-11-18 (5,956 flights) | docs/testing/test-report.md |
| Model quality (test weeks) | AUC 0.798 (15+ min) vs 0.741 baseline; 0.757 (60+ min) vs 0.676 baseline. Missed-connection backtest, no-slack band: 0.70 predicted vs 0.69 observed | docs/testing/test-report.md |
| Reboot test | **Not done**: skipped by decision on 21 Nov 2026 (phase 1 test passed with the same restart policy) | docs/testing/test-report.md |
### Open items
- **Reboot check** for the phase 2 stack: skipped by decision. Until a reboot test passes, phase 2 is reported as deployed with operational verification pending.
- **HTTPS and automated nightly backups:** moved to **phase 6 (Secure and protect)**, which needs separate approval. Phase 2 runs over plain HTTP on :8888 with no automated backup; take a manual `pg_dump` before each deployment (see the deployment guide).
- **Local end-to-end run:** not done on the development machine, because its local bookings Parquet still uses the old `dep_year` layout. The runtime code is identical to the server, so Playwright was run against the server instead (4/4).
- **Trivy scans** of the phase 2 images are not recorded in the phase 2 evidence.
- Model limitations (seven-day view only, independence of inbound and onward delays, over-estimated long delays, inferred aircraft type and capacity): see the [model card](../testing/model-card.md).

## Phase 3 (Agent and what-if)
Date: 21 Nov 2026 · Approved on 21 Nov 2026 · Status: **deployed and verified on `http://<server>:8888`; reboot test not run**

### What was delivered
- **Recovery options** (`backend/app/engine/network.py`, `scenarios.py`): cancel a later round trip of the delayed aircraft (X→Y→X within 24 h, up to 3 pairs), labelled "Consolidate" when every cancelled passenger is rebooked on a same-route flight within 6 h. Every option now has passenger KPIs (passenger delay, cancelled passengers, passengers without a seat) from a CP-SAT rebooking. Design: [ADR 0011](../architecture/adr/0011-cancel-consolidate-and-strategies.md).
- **Strategies** (`backend/app/engine/strategy.py`): lowest cost (default, unchanged ranking), protect passengers, least delay. API `POST /api/v1/scenarios/{id}/strategy`; the strategy is stored with the scenario.
- **Agent** (`backend/app/agent/`, `backend/app/agent_api.py`): recommend-only Claude agent on the Messages API with 8 read-only tools, limits of 12 tool calls and 120 s, and a rule-based planner fallback. Runs are stored in the new `agent_runs` table (Alembic 0002). API `POST /api/v1/agent/runs`, `GET /api/v1/agent/runs/{id}`, `GET /api/v1/agent/runs`. Design: [ADR 0010](../architecture/adr/0010-tool-using-agent.md); behaviour and evidence: [agent card](../testing/agent-card.md).
- **UI:** "Strategies compared" panel and option kinds in the delay view (`StrategyPanel.tsx`, `DelayView.tsx`); "Ask the agent" tab in the launcher and button on watchlist flights; Agent tab with live steps, recommendation and "Open scenario to review and approve" (`AgentRunView.tsx`).
- **Settings:** `AGENT_EFFORT`, `AGENT_MAX_TOOL_CALLS`, `AGENT_TIMEOUT_SECONDS` (README, `settings.env.example`, `compose.yml`).
- **Documentation:** SYSTEM_ARCHITECTURE §11, ADRs 0010–0011, plan, agent card, this report, test report, deployment guide, README, methods PDF v1.2, Confluence page.
- **Also live in this deployment:** Air Arabia UI theme, confusion-matrix model evaluation.

### Verification
| Check | Result | Evidence |
|---|---|---|
| Quality gate (`scripts/check.sh`) | Pass: 69 backend, 19 frontend tests, lint, strict types, build | docs/testing/test-report.md |
| Live agent probe before deploy (server data, real API, read-only container) | G9519, no delay given: used the 56-min planning delay; 7 tool calls in 37 s; recommended `swap:A6-ANO` | docs/testing/test-report.md |
| Scenario time with the new options (real data) | 0.6–7 s per delay scenario | docs/testing/test-report.md |
| Server deployment | Deployed 2026-11-21 02:31 UTC; rollback image tags api/web `pre-202611210231`; database dump `~/backups/disruption-advisor/pre-202611210231.dump`; Alembic 0002 applied (`agent_runs`) | docs/testing/test-report.md |
| Smoke test on the server | 11/11 | docs/testing/test-report.md |
| Playwright on the server | 6/6, including "phase 3: strategies switch the recommendation" and "phase 3: the agent investigates a flight and its recommendation opens for approval" | same log |
| Agent run on the server (during the e2e run) | G9901_202611220500: source `ai:claude-opus-5-5`, 7 steps, 25 s, recommended `swap:A6-AOH` under "protect passengers" | same log |
| Reboot test | **Not run** for phase 3 | – |
### Open items
- **Reboot test** for the phase 3 stack: not run. Until it passes, phase 3 is reported as deployed with operational verification pending.
- **Phase 6 (HTTPS and nightly backups):** still needs approval. Take a manual `pg_dump` before each deployment (see the deployment guide).
- **Revenue loss of cancellations is not modelled** (no fare revenue per flight is supplied). This is a stated assumption in every delay scenario.
- **E2E type check:** `e2e/tsconfig.json` needs `@types/node` in the e2e `devDependencies` for a standalone `tsc` run. This predates phase 3; Playwright itself runs fine.
- Agent limits (output varies between runs, a restart fails a running run): see the [agent card](../testing/agent-card.md).
