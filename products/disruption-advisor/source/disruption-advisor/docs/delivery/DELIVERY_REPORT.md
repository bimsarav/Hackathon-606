# Delivery Report

Phase 1 (MVP): 20 Nov 2026, **deployed and verified**. Phase 2 (Predict): 21 Nov 2026, **deployed and verified; reboot check pending** (see [Phase 2](#phase-2-predict)).

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
| Reboot test (engineering standards §14.5) | Passed: back in ~50 s, healthy with no manual action, data intact | deployment guide |

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
Date: 21 Nov 2026 · Approved by the user on 21 Nov 2026 · Status: **deployed and verified on `http://<server>:8888`; reboot check pending**

### What was delivered
- **Delay-risk model** (`backend/app/ml/delay_risk.py`): LightGBM, one classifier per delay threshold (5–180 min), recency-weighted, features known 7 days ahead, TreeSHAP reasons in plain words, an arrival-delay curve and a missed-connection probability per connecting passenger. It runs as ingest stage 3 and retrains on every data load. Details: [model card](../testing/model-card.md).
- **API** (`backend/app/risk.py`, read-only, sign-in required): `GET /api/v1/risk/watchlist`, `/api/v1/risk/flights/{flight_id}`, `/api/v1/risk/model`.
- **UI:** "Delay watchlist (7 days)" tab with risk filter and sort; a flight opens its reasons and the connecting passengers at risk; "Analyse a N min delay" opens Scenario A with the planning delay. Teammate addition in the same release: a before/after aircraft rotation board in the delay view (`frontend/src/RotationBoard.tsx`).
- **Documentation:** SYSTEM_ARCHITECTURE §10, ADR 0008 (delay-risk model), ADR 0009 (HTTPS and backups, deferred to phase 6), model card, this report, test report, deployment guide, methods PDF, Confluence page.

### Verification
| Check | Result | Evidence |
|---|---|---|
| Quality gate (`scripts/check.sh`) | Pass: 47 backend, 9 frontend tests, lint, strict types, build | `execution/logs/output/T-504-check-merged.log` |
| Server code | Server tree identical to the verified local tree (86 files, SHA-256) | `execution/logs/execution.log`, T-506 |
| Smoke test on the server | 11/11 | `execution/logs/output/T-506-smoke-prod.log` |
| Playwright on the server | 4/4, including the new watchlist test | `execution/logs/output/T-506-e2e-prod.log` |
| Risk API on the server | Watchlist: 1,491 flights in 7 days, 18 high and 140 medium risk. Model card: train 2026-01-01 .. 2026-10-21 (57,104 flights), test 2026-10-21 .. 2026-11-18 (5,956 flights) | `execution/logs/output/T-506-risk-api-prod.log` |
| Model quality (test weeks) | AUC 0.798 (15+ min) vs 0.741 baseline; 0.757 (60+ min) vs 0.676 baseline. Missed-connection backtest, no-slack band: 0.70 predicted vs 0.69 observed | same log; `execution/logs/execution.log`, T-502/503 |
| Reboot test (engineering standards §14.5) | **Not done yet**: pending user approval | – |

The `execution/` paths are in the project workspace, not in this repository.

### Open items
- **Reboot check** for the phase 2 stack: pending user approval. Until it passes, phase 2 is reported as deployed with operational verification pending.
- **HTTPS and automated nightly backups:** moved by the user to **phase 6 (Secure and protect)**, which needs separate approval. Phase 2 runs over plain HTTP on :8888 with no automated backup; take a manual `pg_dump` before each deployment (see the deployment guide).
- **Local end-to-end run:** not done on the development machine, because its local bookings Parquet still uses the old `dep_year` layout. The runtime code is identical to the server, so Playwright was run against the server instead (4/4).
- **Trivy scans** of the phase 2 images are not recorded in the phase 2 evidence.
- Model limitations (seven-day view only, independence of inbound and onward delays, over-estimated long delays, inferred aircraft type and capacity): see the [model card](../testing/model-card.md).
