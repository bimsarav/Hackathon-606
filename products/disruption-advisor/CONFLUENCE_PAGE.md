# Disruption Advisor (UC5: Flight and Passenger Disruption Management)

## Overview
Disruption Advisor helps the Operations Control Centre (OCC) and the Passenger Control Unit (PCU) handle a flight disruption before its impact cascades through the network. For a delayed or cancelled flight it:
- shows which later flights and which passenger connections are affected over the next 7 days;
- compares recovery options (absorb, aircraft swap, cancel or consolidate a round trip) on delay, missed connections, passengers and cost, and recommends one under the chosen strategy;
- ranks the affected passengers transparently and rebooks them within the seats that are actually available;
- explains every recommendation and drafts passenger messages;
- on request, lets an AI agent investigate a flight step by step and recommend an option (phase 3).

It only recommends. A person approves or rejects each action, and every decision is audited.

- **Status:** Phase 1 (MVP) deployed and verified on 20 Nov 2026, including a server reboot test. Phase 2 (Predict) deployed and verified on 21 Nov 2026; its reboot check was skipped by decision. Phase 3 (Agent and what-if) deployed and verified on 21 Nov 2026 (smoke and Playwright on the server); no reboot test was run for it. The demo runs over plain HTTP with no automated database backup; HTTPS and backups are phase 6, which needs approval.
- **Demo:** UI http://92.5.154.198:8080; API http://92.5.154.198:8888/api/... (OpenAPI docs at /api/docs). Both are plain HTTP; demo sign-ins are shared separately.
- **Roles:** as of now the distinct roles are **OCC** and **Evaluator** (the Evaluator also sees the Model Card and Test data views). The **PCU** role has the same access as OCC; only the audit trail records the role name.
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
| More recovery options: cancel a later round trip of the delayed aircraft, or consolidate it onto other flights on the same route; passengers rebooked with the phase 1 rules | Done (phase 3, 21 Nov 2026) |
| Strategies compared: lowest cost, protect passengers, least delay; switching the strategy changes the recommendation | Done (phase 3, 21 Nov 2026) |
| AI agent: investigates a flight with read-only engine tools, shows its steps live and recommends an option for approval; rule-based planner when the AI is unavailable | Done (phase 3, 21 Nov 2026) |
| Scenario B: cancellation with limited seats; passengers ranked by tier and weighted score; rebooking with an optimiser that keeps bookings together | Done |
| What-if: adjustable priority weights | Done |
| History data: G9 flights 1 Jan to 18 Nov 2026 with actual times, aircraft chains (actual order), delay codes, diversions and bookings (`history_flights.parquet`), for backtests and prediction | Done (used by the phase 2 delay-risk model) |
| Backtest of delay propagation on 1,634 real delays (Jan-Nov 2026): mean error 25 min vs 57 min without knock-on; next-leg delays caught 97% at 99.7% precision. Median recovery turns (60/48 min) reduce the error to 22 min. `python -m app.backtest`, docs/testing/backtest.md | Done |
| Synthetic passenger ID, passport and national ID per person over all bookings Oct 2025 - Mar 2027 (6.29M persons, same IDs in the app and the shared export). Since 21 Nov 2026 the bookings are stored without names (name-free format by departure month) and passengers are shown by their synthetic passenger ID | Done |
| Name-free bookings format (21 Nov 2026): the ingest accepts the bookings as name-free Parquet by departure month, or converts the zip to that format; `python -m app.ingest.share` copies them (about 950 MB) for a shared drive, never Git | Done |
| Plain-English explanations and passenger message drafts (Claude AI, with template fallback) | Done |
| Approve or reject with an audit trail; demo roles (OCC and Evaluator are distinct; PCU has the same access as OCC) | Done |
| Approve a non-recommended option (override with a required reason, audited) | Done (21 Nov 2026) |
| Before/after aircraft rotation board in the delay view | Done (21 Nov 2026) |
| Delay prediction: 7-day delay watchlist with reasons and per-passenger missed-connection risk | Done (phase 2, 21 Nov 2026; see below) |
| HTTPS, automated backups, crew legality, equipment change | Not done (later phases) |
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

## Phase 3: Agent and what-if (21 Nov 2026)
**What it does.** Phase 3 gives more ways to recover from a delay, lets you compare them under different goals, and adds an AI agent that does the investigation for you. The engine still computes every number, and a person still approves every action.

**Recovery options.** For a delayed flight the options table now shows up to four kinds of option:
- **Absorb:** the aircraft keeps its flights and the delay runs down its rotation.
- **Swap:** a same-type aircraft takes over the remaining flights (up to 3 candidates).
- **Cancel round trip:** a later out-and-back pair on the delayed aircraft (X→Y→X, within 24 hours; up to 3 pairs) is cancelled. The aircraft catches up its schedule without another aircraft, and is back where it was planned to be. The passengers of the cancelled flights are ranked and rebooked with the phase 1 rules (tiers, weights, seats actually free, bookings kept together), with care and EU261 estimates.
- **Consolidate:** the same as a cancellation, shown under this name when every passenger of the cancelled flights gets a seat on another flight on the same route within 6 hours.

Every option shows its cost, aircraft delay, passenger delay, missed connections, cancelled passengers and passengers left without a seat. Rebooking is checked for every option, so you can compare them fairly. Revenue lost by a cancellation is not counted (no fare revenue per flight was supplied).

**Strategies.** The **Strategies compared** panel in the delay view shows the pick of each strategy side by side:

| Strategy | Picks the option with the lowest… (then the next column breaks ties) |
|---|---|
| Lowest cost (default, as in phases 1–2) | cost, then missed connections, then aircraft delay |
| Protect passengers | passengers without a seat, then passengers disrupted (missed connections + cancelled), then passenger delay, then cost |
| Least delay | passenger delay, then cost |

"Passenger delay" adds up the delay of every passenger on a late flight, the arrival delay of every rebooked passenger, and 24 hours for each passenger without a seat (an assumption, listed under the assumptions). To switch, click a strategy in the panel. The numbers do not change; only the recommended option does. Approving an option that is not the active strategy's pick is an override and needs a reason, as before.

**How to ask the agent.**
1. Open the **Ask the agent** tab in the launcher. Optionally choose a delay (or let the agent use the predicted one), a strategy (or no preference) and a note, for example a crew limit you know about. Then pick a flight from the list or search.
   Or: in the **Delay watchlist**, open a flight and click **Ask the agent**. The agent gets the flight and its planning delay.
2. The **Agent** tab shows the run. Each step appears live: the agent's short note, the tool it used and a one-line result (for example "5 options; picks: …"). An AI run takes about 20–60 seconds; the rule-based planner takes a few seconds.
3. When it is done, the run shows the recommended option, the strategy, 2–4 reasons, risks and the checks you should make (for example crew legality or aircraft readiness).
4. Click **Open scenario to review and approve**. The scenario opens in the normal delay view with the agent's recommendation. Approve it, or approve another option as an override with a reason. Both are audited.

If a run fails, **Try again** starts it with the same inputs. You can have one run in progress at a time. Recent runs are listed in the Agent tab.

**Guardrails.**
- **Recommend only.** The agent can only read data through the engine. It changes nothing and approves nothing.
- **Engine numbers.** The agent must choose one of the options the engine produced. All figures on screen come from the engine, not from the agent's text.
- **No personal data to the AI.** The agent sees flight facts and counts only: no names, booking references, passenger IDs, document numbers or contact details. A test checks every request.
- **Limits.** At most 12 tool calls and 120 seconds per run.
- **Rule-based planner.** When the AI is not configured, refuses, fails or hits a limit, a rule-based planner runs the same tools in a fixed order and recommends the chosen strategy's pick. The run is labelled with its source, and the AI's steps so far stay visible.

Agent details: `docs/testing/agent-card.md`; design: `docs/architecture/SYSTEM_ARCHITECTURE.md` §11 and ADRs 0010–0011.

## Phase 5: passenger rewards and the 7-day tab (21 Nov 2026)
**What it does.** After a delay or cancellation, a planner enters a goodwill budget in AED and the system recommends a reward for each passenger of the flight: a meal voucher, gift voucher, lounge pass, loyalty miles or a free ticket. It is recommend-only: the plan is approved through the audit log and nothing is sent to passengers.

**How the recommendation is built.**
1. **Disruption severity (0 to 100) per passenger:** from the delay (up to 50 points for 4 hours), a cancellation (60), a missed connection (+25), the wait for the next flight (up to 15) and a vulnerable passenger (+10).
2. **Passenger value (0 to 100):** the passenger's recovery-priority score (loyalty, frequency, fare, extras, journey, family) as a rank among the flight's passengers.
3. **Target amount:** up to AED 600, scaled by severity and value.
4. **Allowed rewards:** a meal voucher only for 60+ minutes and when the care plan gives no meals; a lounge pass only for 120+ minutes and no hotel; miles for loyalty members only; a free ticket for severe cases; everything within the target. Care (meals, hotel, transport, refund option) stays separate and is never repeated.
5. **Chance of acceptance:** a LightGBM model trained on **simulated** redemption history (no real history exists), with proxy rules as the fallback. It scores AUC 0.70 on held-out passengers against 0.665 for the rules and 0.615 for the reward type's average; the best possible on the simulated data is 0.74.
6. **Choosing and fitting the budget:** utility = severity x value x chance of acceptance x square root of the cost. If the plan is over budget, the cheapest-to-lose steps are scaled down until it fits. The plan never exceeds the budget.

**Upcoming flights.** The plan also looks at what each passenger has booked after the flight: a connection, a return or later flights. In a cancellation a booked connection adds 12 severity points and a booked return 6, because the rest of the journey is affected. Flights coming up make vouchers, miles and tickets more likely to be used, and a connection through the hub makes a lounge pass more likely. The "More data" view shows the next flight.

**Screen.** The delay and cancellation views have one passenger panel with two tabs: connection passengers, and rewards / compensation. The reward table shows the passenger, the recommended reward and its value; "More data" shows severity, value, target, the chance of acceptance and the reasons.

**7-day tab.** The tab now shows last month's cascade check in the sidebar (the scenario launcher is hidden there): the formula *next departure = max(scheduled departure, previous arrival + 40 min)* against real departures, as six boxes (1,656 pairs, mean delta +10 min, 75% within 15 minutes, 93% within 30 minutes, 412 under- and 1 over-estimates for 19 Oct to 18 Nov). "Expand the full view" opens the scatter, the delta histogram and the table of all pairs.

**Models tuned.** The delay model and the reward model were both tuned with Optuna and compared with other models on time-ordered or grouped validation; the tuning of the reward model gained almost nothing. An added delay feature, `month`, raises ranking slightly but lowers the validation score, so it is flagged for a decision.

**Limits.** The reward preferences come from simulated data and the reward values and weights are assumptions to confirm with the airline. Details: `docs/architecture/REWARDS_DESIGN.md`, `docs/testing/reward-model-card.md`, `docs/testing/reward-model-selection.md`.

## Architecture
```
 Browser (OCC / PCU / Evaluator)     API clients
        |  UI: HTTP :8080                  |  API: HTTP :8888 (direct)
        v                                  v
 +------------------+      +---------------------------------------------+
 | web: nginx       |----->| api: FastAPI                                |
 | React app, CSP,  | /api | impact, recovery, priority, rebooking,       |
 | login rate limit |      | explanations, decisions, delay risk          |
 +------------------+      +----+--------------------+-------------------+
                                |                    |                   |
                                v                    v                   v
                      +----------------+  +--------------------+  Claude API
                      | PostgreSQL 18  |  | ops data (Parquet, |  (wording; agent
                      | scenarios,     |  | read by DuckDB)    |   tool use; no
                      | decisions,     |  +---------^----------+   personal data
                      | agent runs     |            |              sent)
                      +----------------+            |
                                          +---------+----------+
                                          | ingest (one-shot): |
                                          | airline extracts   |
                                          | -> typed Parquet,  |
                                          | delay-risk model   |
                                          +--------------------+
```
- **Data stores:** PostgreSQL holds what users create (scenarios, decisions and, since phase 3, agent runs with their steps). Parquet files queried with DuckDB hold the airline extracts and, since phase 2, the delay-risk scores and model card.
- **Services (Docker Compose):** `db`, `migrate` (one-shot), `ingest` (one-shot), `extracts-db` (one-shot), `api` (published on port 8888), `web` (published on port 8080; its own `/api` calls go to `api` inside Compose). Ports and their risks: ADR 0015 in the repository.

## Technology stack
| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic 2 |
| Analytics data | Apache Parquet, DuckDB 2.0, pyarrow, python-calamine |
| Optimisation | Google OR-Tools CP-SAT 9.15 |
| Prediction | LightGBM 4.7 with built-in TreeSHAP explanations |
| Generative AI | Anthropic Claude API (claude-opus-5-5): explanations grounded on engine facts with template fallback; phase 3 agent with tool use (Messages API) and a rule-based planner fallback |
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

  Phase 3 adds cancelling or consolidating a later round trip. The default strategy recommends the cheapest option; "protect passengers" and "least delay" order the same options differently.
- **Passenger priority:** strict tiers first: mandated care (special assistance, infants), then urgency (onward connections), then others; non-revenue passengers come last. Inside a tier, a weighted score orders passengers: loyalty, travel frequency, fare, ancillaries, journey, family or group.
- **Rebooking:** a 0/1 integer programme (CP-SAT) keeps bookings together and never exceeds free seats. It returns a proven optimal plan in under a second.
- **Explainability by design:** every number traces to a formula, with points per attribute, the tier rule, a cost breakdown and seat reasons. The AI only words the engine's facts.
- **Agent (phase 3):** Claude calls read-only engine tools in a loop (at most 12 calls, 120 s) and submits one engine option with reasons, risks and checks. A rule-based planner gives the same kind of answer without the AI.
- **Delay risk (phase 2):** one LightGBM classifier per delay threshold (5 to 180 minutes), trained on the 2026 history with recent months weighted more, using only features known 7 days ahead. Reasons come from SHAP contributions. Missed-connection risk combines the inbound arrival-delay and onward departure-delay predictions with the connection's spare time after MCT.

The full methods document with references is `docs/delivery/Disruption_Advisor_Methods.pdf` in the repository.

## Environments and deployment
| Environment | Where | Notes |
|---|---|---|
| Local | Docker Compose on a workstation | `docker compose up -d --build` |
| Demo | OCI VM: UI port 8080, API port 8888 (HTTP) | Secrets only in the server `settings.env` (mode 600); automatic restart verified by a reboot test on 20 Nov 2026 (phase 1). Phase 2 deployed 21 Nov 2026 (reboot check skipped by decision). Phase 3 deployed 21 Nov 2026 02:31 UTC with rollback image tags and a database dump taken first; no reboot test run. No automated backup yet (phase 6) |

**Agent settings (phase 3)**, in `settings.env`:

| Setting | Default | Meaning |
|---|---|---|
| `AGENT_EFFORT` | `medium` | How much the model thinks per step |
| `AGENT_MAX_TOOL_CALLS` | `12` | Tool calls per run before the planner takes over |
| `AGENT_TIMEOUT_SECONDS` | `120` | Time per run before the planner takes over |

The agent uses the same `ANTHROPIC_API_KEY` and `AI_MODEL` as the explanations. Without a key, every run is answered by the rule-based planner.

## How to build, run and test
```
scripts/init-settings.sh        # creates settings.env (visible) + the .env link Compose reads; then fill it in
docker compose up -d --build    # first ingest takes 4-15 minutes
scripts/check.sh                # lint, types, 69 backend tests, 19 frontend tests, build
scripts/e2e.sh                  # Playwright end-to-end tests against the running stack
scripts/smoke.sh <ui-url> <api-url>   # post-deployment smoke test (UI port, then API port)
```

## API summary
The API is published directly on port 8888 (`http://92.5.154.198:8888/api/...`); the UI on port 8080 calls the same endpoints through its own `/api`.

| Endpoint | Purpose |
|---|---|
| POST /api/v1/auth/login | Sign in (rate limited) |
| GET /api/v1/meta, /api/v1/presets, /api/v1/flights | Context, suggested scenarios, flight search |
| POST /api/v1/scenarios | Run a delay or cancellation analysis |
| POST /api/v1/scenarios/{id}/reprioritise | What-if with new weights |
| POST /api/v1/scenarios/{id}/select | Show another option (passengers, costs, explanation) |
| POST /api/v1/scenarios/{id}/strategy | Switch the strategy; the recommendation follows (phase 3) |
| GET or POST /api/v1/scenarios/{id}/decisions | Audit trail; approve or reject |
| POST /api/v1/scenarios/{id}/messages | Passenger message draft |
| GET /api/v1/risk/watchlist | 7-day delay watchlist (phase 2) |
| GET /api/v1/risk/flights/{flight_id} | One flight's delay risk, reasons and connecting passengers at risk |
| GET /api/v1/risk/model | Model card: data, features, test results |
| GET /api/v1/risk/cascade | Last month's cascade formula check (read-only) |
| POST /api/v1/scenarios/{id}/rewards | Goodwill reward plan within a budget (phase 5); approve through /decisions |
| POST /api/v1/agent/runs | Start an agent run on a flight (optional delay, strategy, note); returns at once (phase 3) |
| GET /api/v1/agent/runs/{id}, GET /api/v1/agent/runs | One run with its steps and recommendation; recent runs |
| /api/docs | OpenAPI documentation |

## Security
- **Sign-in:** demo authentication; distinct roles OCC and Evaluator (PCU has the same access as OCC); signed expiring tokens; a rate limit on sign-in on the UI port 8080 (not on the API port 8888). Production will use the airline's identity provider (OIDC).
- **Secrets:** only in the server `settings.env`; never in the repository. The airline data is git-ignored and mounted read-only.
- **AI data sharing:** no names, booking references, passenger IDs, document numbers or contact details are sent to the AI service. This includes the phase 3 agent, whose tools return flight facts and counts only.
- **Hardening:** security headers (CSP, nosniff, frame deny), non-root containers, input validation, consistent error responses.
- **Scans:** Trivy found 0 HIGH or CRITICAL vulnerabilities. The secret-scanner hits in the Anthropic SDK's documentation text are false positives.

## Test results (phase 1: 20 Nov 2026; phases 2 and 3: 21 Nov 2026)
| Test | Result |
|---|---|
| Backend unit and API tests (incl. PostgreSQL via Testcontainers) | 69 passed (phase 3); phase 5 adds 30 tests: 73 passed locally without Docker, 26 need the PostgreSQL container (the new API tests also passed on SQLite) |
| Frontend unit tests | 24 passed (phase 5 and the 7-day tab; local) |
| Playwright end-to-end on the demo server | 6 passed (phase 3, incl. "strategies switch the recommendation" and "the agent investigates a flight and its recommendation opens for approval"); phase 2: 4; phase 1: 3 |
| Smoke test on the demo server | 11 of 11 passed (phases 1, 2 and 3) |
| Agent run on the demo server | Flight G9901 (22 Nov): AI source, 7 steps in 25 s, recommended the swap with A6-AOH under "protect passengers" |
| Server reboot test | Phase 1 passed: back in about 50 s, all services healthy without manual action, data intact. Phase 2: skipped by decision. Phase 3: not run |
| Delay-risk model, test weeks | AUC 0.798 (15+ min) and 0.757 (60+ min) vs 0.741 and 0.676 for the route × hour baseline |
| Real-data example | G9519 delayed 150 min: swap with A6-ARI costs AED 70,875 vs AED 222,600 to absorb the delay |
| Delay scenario time with the phase 3 options (real data) | 0.6 to 7 s per scenario |

## Known limitations and open decisions
- **Synthetic fields:** fare family and most special-assistance codes are synthetic (labelled), because the extracts do not contain them.
- **Loyalty (modelled on the airline's loyalty sample):**
  - **Membership** is real (the booking flag).
  - **Tier and priority:** Basic, Silver, Gold and Platinum, with recovery priority Lowest, Low, Medium and High, as in the sample.
  - **Synthetic account per member:** a loyalty ID and a points balance. The tier comes from real flights flown in the last 12 months.
  - **Family accounts:** a booking travelling with children or infants becomes a family account under a head of family. Everyone on it travels on the head's tier, so a child or a non-member partner is not ranked below the head.
  - **Screen:** the passenger list shows the tier, its priority and "family account" or "head of family".
- **Assumed rules:** costs and the 50-minute default MCT (lowest real SHJ rule) are assumptions; turn times are measured. All are configurable.
- **Carriers:** G9 flights only; partner and other carriers in the extracts are excluded (future enhancement).
- **Crew:** legality is not checked; no crew data was supplied.
- **Capacity:** exact from the inventory extract for 1,727 of 2,614 window flights; inferred from the most passengers carried for 426, assumed A320 (174 seats) for 461.
- **Approval:** approving an option other than the recommended one is an override and needs a reason.
- **Cancellations:** lost fare revenue is not counted in the cost of a cancel or consolidate option.
- **Agent:** its wording and step order vary between runs; the options and numbers do not. A run interrupted by a server restart shows as failed and must be started again.
- **Connection:** HTTP only on both ports, and no automated database backup; HTTPS and backups are phase 6 (needs approval). The API on port 8888 is published directly: no sign-in rate limit there, and the address it logs can be set by the client (ADR 0015).
- **Predictions:** see the phase 2 limitations above.
- **Open questions:** listed in the project's clarification register.

## Roadmap
| Phase | Content | Status |
|---|---|---|
| 1 MVP | Scenarios A and B, explanations, approvals, hosting | Done |
| 2 Predict | Delay-risk prediction with explanations (LightGBM, SHAP), 7-day watchlist, per-passenger missed-connection risk | Deployed 21 Nov 2026 and verified (smoke, Playwright); reboot check skipped by decision |
| 3 Agent and what-if | AI agent coordinating the steps; cancel or consolidate as recovery options; strategy comparison | Deployed 21 Nov 2026 and verified (smoke 11/11, Playwright 6/6, agent run on the server); reboot test not run |
| 4 Extend | Partner and other carriers, unaccompanied minors, equipment change, bus legs, crew legality, real data feeds, CI/CD and monitoring | Not started (needs approval) |
| 6 Secure and protect | HTTPS (Caddy, sslip.io hostname) and nightly PostgreSQL backups with a restore test; moved out of phase 2 on 21 Nov 2026. No phase 5 is defined | Not started (needs approval) |

## Contacts and ownership
| Role | Name |
|---|---|
| Product owner | `<product-owner>` |
| Clarifications | `<business-analyst>` |
| Engineering | `<engineering-contact>` |
| Operations (server) | `<operations-contact>` |
