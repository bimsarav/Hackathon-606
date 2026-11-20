# Disruption Advisor (UC5: Flight and Passenger Disruption Management)

## Overview
Disruption Advisor helps the Operations Control Centre (OCC) and the Passenger Control Unit (PCU) handle a flight disruption before its impact cascades through the network. For a delayed or cancelled flight it:
- shows which later flights and which passenger connections are affected over the next 7 days;
- compares recovery options on delay, missed connections and cost, and recommends one;
- ranks the affected passengers transparently and rebooks them within the seats that are actually available;
- explains every recommendation and drafts passenger messages.

It only recommends. A person approves or rejects each action, and every decision is audited.

- **Status:** Phase 1 (MVP) deployed and verified on 20 Nov 2026, including a server reboot test. Phase 2 has not started.
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
| Synthetic passenger ID, passport and national ID per person (same person keeps them across bookings); API shows initials only, never full names | Done |
| Plain-English explanations and passenger message drafts (Claude AI, with template fallback) | Done |
| Approve or reject with an audit trail; demo roles OCC and PCU | Done |
| Approve a non-recommended option (override with reason) | Not done (proposed) |
| Delay prediction, HTTPS, AI agent, cancellation as a recovery option, crew, equipment change | Not done (later phases) |

## Architecture
```
 Browser (OCC / PCU)
        |  HTTP :8888 (HTTPS in phase 2)
        v
 +------------------+      +---------------------------------------------+
 | web: nginx       |----->| api: FastAPI                                |
 | React app, CSP,  | /api | impact, recovery, priority, rebooking,       |
 | login rate limit |      | explanations, decisions                      |
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
                                          | -> typed Parquet   |
                                          +--------------------+
```
- **Data stores:** PostgreSQL holds what users create (scenarios, decisions). Parquet files queried with DuckDB hold the airline extracts.
- **Services (Docker Compose):** `db`, `migrate` (one-shot), `ingest` (one-shot), `api`, `web`.

## Technology stack
| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic 2 |
| Analytics data | Apache Parquet, DuckDB 2.0, pyarrow, python-calamine |
| Optimisation | Google OR-Tools CP-SAT 9.15 |
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
- **Passenger priority:** strict tiers first: mandated care (special assistance, unaccompanied minors, infants), then urgency (onward connections), then others; non-revenue passengers come last. Inside a tier, a weighted score orders passengers: loyalty, travel frequency, fare, ancillaries, journey, family or group.
- **Rebooking:** a 0/1 integer programme (CP-SAT) keeps bookings together and never exceeds free seats. It returns a proven optimal plan in under a second.
- **Explainability by design:** every number traces to a formula, with points per attribute, the tier rule, a cost breakdown and seat reasons. The AI only words the engine's facts.

The full methods document with references is `docs/delivery/Disruption_Advisor_Methods.pdf` in the repository.

## Environments and deployment
| Environment | Where | Notes |
|---|---|---|
| Local | Docker Compose on a workstation | `docker compose up -d --build` |
| Demo (MVP) | OCI VM, port 8888 | Secrets only in the server `.env` (mode 600); automatic restart verified by a reboot test on 20 Nov 2026 |

## How to build, run and test
```
cp .env.example .env            # set INPUT_DIR, passwords, DEMO_USERS, TOKEN_SECRET, optional ANTHROPIC_API_KEY
docker compose up -d --build    # first ingest takes 4-15 minutes
scripts/check.sh                # lint, types, 22 backend tests, 5 frontend tests, build
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
| /api/docs | OpenAPI documentation |

## Security
- **Sign-in:** demo authentication with two roles, signed expiring tokens and a rate limit on sign-in. Production will use the airline's identity provider (OIDC).
- **Secrets:** only in the server `.env`; never in the repository. The airline data is git-ignored and mounted read-only.
- **AI data sharing:** no names, booking references or contact details are sent to the AI service.
- **Hardening:** security headers (CSP, nosniff, frame deny), non-root containers, input validation, consistent error responses.
- **Scans:** Trivy found 0 HIGH or CRITICAL vulnerabilities. The secret-scanner hits in the Anthropic SDK's documentation text are false positives.

## Test results (20 Nov 2026)
| Test | Result |
|---|---|
| Backend unit and API tests (incl. PostgreSQL via Testcontainers) | 22 passed |
| Frontend unit tests | 5 passed |
| Playwright end-to-end, local and demo server | 3 passed on each |
| Smoke test on the demo server | 11 of 11 passed |
| Server reboot test | Passed: back in about 50 s, all services healthy without manual action, data intact |
| Real-data example | G9519 delayed 150 min: swap with A6-ARI costs AED 70,875 vs AED 222,600 to absorb the delay |

## Known limitations and open decisions
- **Synthetic fields:** loyalty tier, fare family and most special-assistance codes are synthetic (labelled), because the extracts do not contain them.
- **Assumed rules:** costs and the 50-minute default MCT (lowest real SHJ rule) are assumptions; turn times are measured. All are configurable.
- **Crew:** legality is not checked; no crew data was supplied.
- **Capacity:** inferred for most flights; the inventory extract covers only 6 flights in the demo window.
- **Approval:** only the recommended option can be approved (override is proposed).
- **Connection:** HTTP only until phase 2.
- **Open questions:** listed in the project's clarification register.

## Roadmap
| Phase | Content | Status |
|---|---|---|
| 1 MVP | Scenarios A and B, explanations, approvals, hosting | Done |
| 2 Predict | Delay-risk prediction with explanations (LightGBM, SHAP), 7-day watchlist, HTTPS, nightly backups | Not started (needs approval) |
| 3 Agent and what-if | AI agent coordinating the steps; cancel or consolidate as recovery options; strategy comparison | Not started (needs approval) |
| 4 Extend | Equipment change, bus legs, crew legality, real data feeds, CI/CD and monitoring | Not started (needs approval) |

## Contacts and ownership
| Role | Name |
|---|---|
| Product owner | `<product-owner>` |
| Clarifications | `<business-analyst>` |
| Engineering | `<engineering-contact>` |
| Operations (server) | `<operations-contact>` |
