# Disruption Advisor (UC5: Flight and Passenger Disruption Management)

## Overview
Disruption Advisor helps the Operations Control Centre (OCC) and the Passenger Control Unit (PCU) handle a flight disruption before its impact cascades through the network. For a delayed or cancelled flight it:
- shows which later flights and which passenger connections are affected over the next 7 days;
- compares recovery options on delay, missed connections and cost, and recommends one;
- ranks the affected passengers transparently and rebooks them within the seats that are actually available;
- explains every recommendation and drafts passenger messages.

It only recommends. A person approves or rejects each action, and every decision is audited.

- **Status:** Phase 1 (MVP) deployed and verified on 20 Nov 2026, including a server reboot test. Phase 2 (Predict) deployed and verified on 21 Nov 2026; its server reboot check is still pending (waiting for user approval). The demo runs over plain HTTP with no automated database backup; HTTPS and backups are phase 6, which needs approval.
- **Demo URL:** http://92.5.154.198:8888 (demo sign-in for the OCC and PCU roles is shared separately)
- **Repository:** `<repository-url>`

## Business problem and goals
A single delay at the Sharjah hub can delay later flights flown by the same aircraft and break many passengers' connections. In the supplied punctuality data, knock-on (reactionary) delay codes account for about 76% of coded delay minutes.

Today OCC, crew control and the PCU each work with different information. The goals:
- **One picture:** see the flight and passenger impact of a disruption in one place.
- **Comparable options:** compare recovery options with their trade-offs (delay, missed connections, cost).
- **Fair priority:** prioritise passengers transparently when seats are short, with legal and care duties always first.
- **Faster action:** move from reactive handling to faster, explained, human-approved decisions.

## Scope and features (MVP)
| Feature | Status |
|---|---|
| Scenario A: delay impact along the aircraft rotation (7 days), connections re-checked against minimum connecting times | Done |
| Recovery options: absorb the delay or swap with a same-type aircraft, with delay, missed connections, EU261 estimate and cost; recommendation | Done |
| Scenario B: cancellation with limited seats; passengers ranked by tier and weighted score; rebooking with an optimiser that keeps bookings together | Done |
| What-if: adjustable priority weights | Done |
| History data: G9 flights 1 Jan to 18 Nov 2026 with actual times, aircraft chains (actual order), delay codes, diversions and bookings (`history_flights.parquet`), for backtests and prediction | Done (used by the phase 2 delay-risk model) |
| Backtest of delay propagation on 1,634 real delays (Jan-Nov 2026): mean error 25 min vs 57 min without knock-on; next-leg delays caught 97% at 99.7% precision. Median recovery turns (60/48 min) reduce the error to 22 min. `python -m app.backtest`, docs/testing/backtest.md | Done |
| Synthetic passenger ID, passport and national ID per person over all bookings Oct 2025 - Mar 2027 (6.29M persons, same IDs in the app and the shared export). Since 21 Nov 2026 the bookings are stored without names (name-free format by departure month) and passengers are shown by their synthetic passenger ID | Done |
| Name-free bookings format (21 Nov 2026): the ingest accepts the bookings as name-free Parquet by departure month, or converts the zip to that format; `python -m app.ingest.share` copies them (about 950 MB) for a shared drive, never Git | Done |
| Plain-English explanations and passenger message drafts (Claude AI, with template fallback) | Done |
| Approve or reject with an audit trail; demo roles OCC and PCU | Done |
| Approve a non-recommended option (override with reason) | Not done (proposed) |
| Before/after aircraft rotation board in the delay view | Done (21 Nov 2026) |
| Delay prediction: 7-day delay watchlist with reasons and per-passenger missed-connection risk | Done (phase 2, 21 Nov 2026; see below) |
| HTTPS, automated backups, AI agent, cancellation as a recovery option, crew, equipment change | Not done (later phases) |
| Partner and other carriers (3L, 3O, E5, 9P, 4P): their flights for rebooking, their aircraft for swaps | Not done (future enhancement; MVP covers G9 only) |
| Unaccompanied minors (priority, supervision, guardian notification) | Not done (future enhancement) |
| Care while waiting: meals by wait time, hotel + transport for long or overnight waits, refund / return option, transit-visa and assistance flags | Done (21 Nov 2026) |

## Phase 2: Predict (21 Nov 2026)
**What it does.** Phase 1 answers "this flight is late, what now?". Phase 2 looks ahead: which flights in the next 7 days are likely to be late, why, and which connecting passengers are likely to miss their onward flight. OCC can plan spare aircraft and turn buffers before the day; PCU can see early which passengers may need rebooking or care.

**How to use the watchlist.**
1. Sign in and open the **Delay watchlist (7 days)** tab.
2. Choose the risk level (high only, medium and high, or all flights) and the order (expected missed connections, or chance of a 60+ minute delay).
3. Each row shows the chance of a 15+ and a 60+ minute delay, a planning delay ("plan for": the delay exceeded with a 20% chance), connecting passengers, expected missed connections and the main reason.
4. Click a flight to see up to three reasons in plain words and the connecting passengers most at risk, with their spare time after the minimum connecting time.
5. **Analyse a N min delay** opens Scenario A for that flight with the planning delay filled in. You can change it, then review the options and approve or reject as usual.

**Risk levels** are based on the chance of a delay of 60 minutes or more (normally about 1 flight in 10): **high** = 30% or more, **medium** = 15–30%.

**How good is it (in plain words).** The model learned from about 57,000 G9 flights between January and October 2026 and was then tested on the 5,956 flights of the following four weeks, which it had not seen. It puts a late flight above an on-time one about 80% of the time for 15+ minute delays and about 76% for 60+ minute delays. The simple alternative (the past delay rate of the same route at the same hour) scores 74% and 68%. For connections with no spare time it predicted a 70% miss rate; 69% were actually missed. At go-live the watchlist held 1,491 flights in the next 7 days, 18 of them high and 140 medium risk. The app shows these numbers under "How good are these predictions?".

**Limitations.**
- A prediction is not a decision. It ranks flights and pre-fills a scenario; a person runs the scenario and approves any action.
- It uses only what is known a week ahead (schedule, aircraft plan, bookings, recent delay rates). On the day, the actual inbound delay in Scenario A is more accurate.
- Reasons show what the model weighed most, not proven causes.
- Delays of 2 hours or more are rare and over-estimated; use those chances to rank, not as levels.
- Inbound and onward delays are treated as independent, and aircraft type and seat capacity are inferred for many flights.
- G9 only. The model retrains on every data load.

Method details: `docs/testing/model-card.md` and the methods PDF in the repository.

## Architecture
```
 Browser (OCC / PCU)
        |  HTTP :8888 (HTTPS in phase 6)
        v
 +------------------+      +---------------------------------------------+
 | web: nginx       |----->| api: FastAPI                                |
 | React app, CSP,  | /api | impact, recovery, priority, rebooking,       |
 | login rate limit |      | explanations, decisions, delay risk          |
 +------------------+      +----+--------------------+-------------------+
                                |                    |                   |
                                v                    v                   v
                      +----------------+  +--------------------+  Claude API
                      | PostgreSQL 18  |  | ops data (Parquet, |  (wording only,
                      | scenarios,     |  | read by DuckDB)    |   no personal
                      | decisions      |  +---------^----------+   data sent)
                      +----------------+            |
                                          +---------+----------+
                                          | ingest (one-shot): |
                                          | airline extracts   |
                                          | -> typed Parquet,  |
                                          | delay-risk model   |
                                          +--------------------+
```
- **Data stores:** PostgreSQL holds what users create (scenarios, decisions). Parquet files queried with DuckDB hold the airline extracts and, since phase 2, the delay-risk scores and model card.
- **Services (Docker Compose):** `db`, `migrate` (one-shot), `ingest` (one-shot), `api`, `web`.

## Technology stack
| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic 2 |
| Analytics data | Apache Parquet, DuckDB 2.0, pyarrow, python-calamine |
| Optimisation | Google OR-Tools CP-SAT 9.15 |
| Prediction | LightGBM 4.7 with built-in TreeSHAP explanations |
| Generative AI | Anthropic Claude API (claude-opus-5-5), grounded on engine facts, template fallback |
| Application database | PostgreSQL 18, SQLAlchemy 2, Alembic |
| Frontend | React 19, TypeScript 7, Vite 8, served by nginx 1.30 |
| Packaging and hosting | Docker, Docker Compose; OCI VM (Frankfurt) |
| Quality | Ruff, mypy strict, pytest, Testcontainers, Vitest, Playwright 1.65, Trivy |

## Methods (summary)
- **Delay propagation:** each later flight departs at the later of its scheduled time and the previous arrival plus a minimum turn measured from G9 2026 actual turns (fastest 5%): 51 minutes at SHJ, 36 minutes at outstations.
- **Recovery options:** absorb the delay, or swap the remaining rotations with a same-type aircraft on the ground at the hub. Each option is costed:
  - delay minutes x AED 400;
  - meal care for passengers delayed 2 hours or more;
  - EU261 compensation for flights departing the EU;
  - missed-connection handling.

  The cheapest option is recommended.
- **Passenger priority:** strict tiers first: mandated care (special assistance, infants), then urgency (onward connections), then others; non-revenue passengers come last. Inside a tier, a weighted score orders passengers: loyalty, travel frequency, fare, ancillaries, journey, family or group.
- **Rebooking:** a 0/1 integer programme (CP-SAT) keeps bookings together and never exceeds free seats. It returns a proven optimal plan in under a second.
- **Explainability by design:** every number traces to a formula, with points per attribute, the tier rule, a cost breakdown and seat reasons. The AI only words the engine's facts.
- **Delay risk (phase 2):** one LightGBM classifier per delay threshold (5 to 180 minutes), trained on the 2026 history with recent months weighted more, using only features known 7 days ahead. Reasons come from SHAP contributions. Missed-connection risk combines the inbound arrival-delay and onward departure-delay predictions with the connection's spare time after MCT.

The full methods document with references is `docs/delivery/Disruption_Advisor_Methods.pdf` in the repository.

## Environments and deployment
| Environment | Where | Notes |
|---|---|---|
| Local | Docker Compose on a workstation | `docker compose up -d --build` |
| Demo | OCI VM, port 8888 (HTTP) | Secrets only in the server `settings.env` (mode 600); automatic restart verified by a reboot test on 20 Nov 2026 (phase 1). Phase 2 deployed 21 Nov 2026; its reboot check is pending. No automated backup yet (phase 6) |

## How to build, run and test
```
scripts/init-settings.sh        # creates settings.env (visible) + the .env link Compose reads; then fill it in
docker compose up -d --build    # first ingest takes 4-15 minutes
scripts/check.sh                # lint, types, 47 backend tests, 9 frontend tests, build
scripts/e2e.sh                  # Playwright end-to-end tests against the running stack
scripts/smoke.sh <base-url>     # post-deployment smoke test
```

## API summary
| Endpoint | Purpose |
|---|---|
| POST /api/v1/auth/login | Sign in (rate limited) |
| GET /api/v1/meta, /api/v1/presets, /api/v1/flights | Context, suggested scenarios, flight search |
| POST /api/v1/scenarios | Run a delay or cancellation analysis |
| POST /api/v1/scenarios/{id}/reprioritise | What-if with new weights |
| GET or POST /api/v1/scenarios/{id}/decisions | Audit trail; approve or reject |
| POST /api/v1/scenarios/{id}/messages | Passenger message draft |
| GET /api/v1/risk/watchlist | 7-day delay watchlist (phase 2) |
| GET /api/v1/risk/flights/{flight_id} | One flight's delay risk, reasons and connecting passengers at risk |
| GET /api/v1/risk/model | Model card: data, features, test results |
| /api/docs | OpenAPI documentation |

## Security
- **Sign-in:** demo authentication with two roles, signed expiring tokens and a rate limit on sign-in. Production will use the airline's identity provider (OIDC).
- **Secrets:** only in the server `settings.env`; never in the repository. The airline data is git-ignored and mounted read-only.
- **AI data sharing:** no names, booking references or contact details are sent to the AI service.
- **Hardening:** security headers (CSP, nosniff, frame deny), non-root containers, input validation, consistent error responses.
- **Scans:** Trivy found 0 HIGH or CRITICAL vulnerabilities. The secret-scanner hits in the Anthropic SDK's documentation text are false positives.

## Test results (phase 1: 20 Nov 2026; phase 2: 21 Nov 2026)
| Test | Result |
|---|---|
| Backend unit and API tests (incl. PostgreSQL via Testcontainers) | 47 passed (phase 2) |
| Frontend unit tests | 9 passed (phase 2) |
| Playwright end-to-end on the demo server | 4 passed (phase 2, incl. the watchlist); phase 1: 3 passed locally and on the server |
| Smoke test on the demo server | 11 of 11 passed (phase 1 and phase 2) |
| Server reboot test | Phase 1 passed: back in about 50 s, all services healthy without manual action, data intact. Phase 2: pending (waiting for user approval) |
| Delay-risk model, test weeks | AUC 0.798 (15+ min) and 0.757 (60+ min) vs 0.741 and 0.676 for the route × hour baseline |
| Real-data example | G9519 delayed 150 min: swap with A6-ARI costs AED 70,875 vs AED 222,600 to absorb the delay |

## Known limitations and open decisions
- **Synthetic fields:** loyalty tier, fare family and most special-assistance codes are synthetic (labelled), because the extracts do not contain them.
- **Assumed rules:** costs and the 50-minute default MCT (lowest real SHJ rule) are assumptions; turn times are measured. All are configurable.
- **Carriers:** G9 flights only; partner and other carriers in the extracts are excluded (future enhancement).
- **Crew:** legality is not checked; no crew data was supplied.
- **Capacity:** exact from the inventory extract for 1,727 of 2,614 window flights; inferred from the most passengers carried for 426, assumed A320 (174 seats) for 461.
- **Approval:** only the recommended option can be approved (override is proposed).
- **Connection:** HTTP only, and no automated database backup; both are phase 6 (needs approval).
- **Predictions:** see the phase 2 limitations above.
- **Open questions:** listed in the project's clarification register.

## Roadmap
| Phase | Content | Status |
|---|---|---|
| 1 MVP | Scenarios A and B, explanations, approvals, hosting | Done |
| 2 Predict | Delay-risk prediction with explanations (LightGBM, SHAP), 7-day watchlist, per-passenger missed-connection risk | Deployed 21 Nov 2026 and verified (smoke, Playwright); reboot check pending |
| 3 Agent and what-if | AI agent coordinating the steps; cancel or consolidate as recovery options; strategy comparison | Not started (needs approval) |
| 4 Extend | Partner and other carriers, unaccompanied minors, equipment change, bus legs, crew legality, real data feeds, CI/CD and monitoring | Not started (needs approval) |
| 6 Secure and protect | HTTPS (Caddy, sslip.io hostname, :8888 kept) and nightly PostgreSQL backups with a restore test; moved out of phase 2 by the user on 21 Nov 2026. No phase 5 is defined | Not started (needs approval) |

## Contacts and ownership
| Role | Name |
|---|---|
| Product owner | `<product-owner>` |
| Clarifications | `<business-analyst>` |
| Engineering | `<engineering-contact>` |
| Operations (server) | `<operations-contact>` |
