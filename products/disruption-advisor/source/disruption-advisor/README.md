# Disruption Advisor

Disruption Advisor helps an airline's Operations Control Centre (OCC) and Passenger Control Unit (PCU) handle a flight disruption before it cascades.
- **Scenario A, delay:** for a delayed flight it shows every later flight on the same aircraft rotation and every passenger connection that breaks over the next 7 days. It compares recovery options (absorb the delay, swap in a same-type aircraft, or, since phase 3, cancel or consolidate a later round trip of the delayed aircraft) on delay, missed connections, passengers and cost, and recommends one.
- **Scenario B, cancellation:** for a cancelled flight it ranks the affected passengers. Strict tiers come first (mandated care, then urgency); configurable weights order passengers inside a tier (loyalty, travel frequency, fare, ancillaries, journey, family/group). It then assigns passengers to alternative flights within the seats actually available, keeping bookings together.
- **Strategies (phase 3):** "Lowest cost" (default), "Protect passengers" and "Least delay" each pick their best option from the same list, shown side by side. Switching the strategy changes the recommendation, not the numbers. Design: [ADR 0011](docs/architecture/adr/0011-cancel-consolidate-and-strategies.md) (`docs/architecture/adr/0011-cancel-consolidate-and-strategies.md`).
- **Test data:** `TEST_DATA_DIR` (default `/testdata`, the `test-data` volume) holds flights the evaluator adds in the *Test data* tab.
- **Agent (phase 3):** on request, a Claude agent investigates a flight with read-only engine tools, shows each step live and recommends one engine option with reasons, risks and checks. The result opens as a normal scenario for approval. A rule-based planner answers when the AI is unavailable. No personal data is sent. Details: [docs/testing/agent-card.md](docs/testing/agent-card.md).
- **Explanations:** every recommendation is explained in plain English, written by Claude when an API key is configured, otherwise by templates, and passenger messages are drafted.
- **Delay watchlist (phase 2):** for the next 7 days it estimates each flight's chance of a late departure, gives the main reasons in plain words, and ranks flights by expected missed connections. Opening a flight shows its connecting passengers at risk and starts Scenario A with a suggested delay. Method and test results: [docs/testing/model-card.md](docs/testing/model-card.md).
- **Human approval:** the tool **only recommends**. A person approves or rejects every action, and each decision is audited.

Stack: Python 3.14 · FastAPI · DuckDB over Parquet · Google OR-Tools (CP-SAT) · LightGBM · Anthropic Claude API · SQLAlchemy 2 · Alembic · PostgreSQL 18 · React 19 + TypeScript + Vite · nginx · Docker Compose · Playwright.
Details: [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) (diagrams) · [docs/delivery/MVP_AND_INCREMENTAL_PLAN.md](docs/delivery/MVP_AND_INCREMENTAL_PLAN.md) · [docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md).

## Roles

As of now there are **two distinct roles**:

| Role | What it can do |
|---|---|
| **OCC** (operations user) | Flight Delay, Cancellation, Predict the Flight Delay (AI agent), Delay Watchlist and Recent Searches; approve, override or reject recovery options, rebooking plans, care, rewards and passenger messages. |
| **Evaluator** | Everything the OCC role can do, plus the **Model Card** and **Test data** views. The API refuses those views to every other role (HTTP 403). |

The **PCU** role exists as a login role (`DEMO_USERS`), but **as of now it has exactly the same views and permissions as OCC**; nothing differs except the role name that the audit trail records with each decision ("occ (OCC)", "pcu (PCU)"). A split between aircraft decisions (OCC) and passenger decisions (PCU) is not built. Where the role checks are: `backend/app/auth.py` (`evaluator_only`) and `frontend/src/App.tsx` (`EVALUATOR_VIEWS`).

## Prerequisites
- Docker Engine 20.10+ with Compose v2.21+. Python, uv, Node and every other tool runs inside containers.
- The airline extracts in one folder:
  - `Flight Rotation.xls`
  - `Flight Inventory.csv`
  - `Flight Schedule.csv`
  - `Connection Time.xlsx`
  - `Flight_Punctuality_Jan-Nov_2026_Combined.xlsx`
  - the bookings, in either form:
    - `parquet/raw/bookings/dep_month=YYYY-MM/*.parquet`: name-free bookings (the current format, used as they are), or
    - `Past & Future Booking Data.zip`: the original extract, converted to the name-free format on the first run.

  They are mounted read-only and never committed.

## Run
```bash
scripts/init-settings.sh  # creates settings.env (visible, mode 600) and the link .env -> settings.env that Compose reads
# then edit settings.env: INPUT_DIR, passwords, DEMO_USERS, TOKEN_SECRET (and optionally ANTHROPIC_API_KEY)
docker compose up -d --build
```
Then open the UI at `http://localhost:${UI_PORT}` (default 8080). The API is published on `http://localhost:${API_PORT}` (default 8888), e.g. `/api/v1/...`; its docs are at `/api/docs` on either port. Ports and their risks: ADR 0015 (`docs/architecture/adr/0015-published-ports-ui-8080-api-8888.md`).

Start-up runs in this order:
1. `db`
2. `migrate` (Alembic)
3. `ingest`: converts the extracts to typed Parquet, builds the operating picture and trains the delay-risk model. It takes about 4 minutes the first time, and skips the work when the inputs are unchanged.
4. `api`
5. `web`

Every long-running service restarts by itself, including after a server reboot.

## How the data is used
- **Stage 1 (`app/ingest/convert.py`):** converts every extract to typed Parquet. Bookings (27.9M rows) are stored **without names**: first and last name are replaced by `customer_key` (hash of the name) and a synthetic identity (`passenger_id`, `passport_number_synthetic`, `national_id_synthetic`, `identity_rule`), partitioned by departure month (`dep_month=YYYY-MM`), zstd. Supplied name-free Parquet is checked and copied in seconds; the zip takes 4–15 minutes. Malformed rows are counted and skipped.
- **Stage 2 (`app/ingest/build.py`):** builds the operating picture for 19–30 Nov 2026, for the carriers in `OPERATING_CARRIERS` (default `G9` only; partner and other carriers are a future enhancement):
  - flights with tail, times and capacity;
  - passenger segments;
  - customer profiles.

  Capacity comes from the inventory allocation (curtail/oversell) where available, otherwise from the aircraft layout inferred from the data.
- **Stage 3 (`app/ml/delay_risk.py`, phase 2):** trains the delay-risk model on the 2026 history (LightGBM, features known 7 days ahead) and scores the window. Writes `flight_risk.parquet`, `connection_risk.parquet` and `model_card.json` to `<data>/ops`. It reruns with stage 2, so every new data drop retrains the model. Details: [docs/testing/model-card.md](docs/testing/model-card.md).
- **Synthetic fields:** the extracts have no loyalty tier, fare family or special-service codes, so these are synthetic, deterministic and labelled in the UI.
- **Fares list** (`fares_list.csv`, or `parquet/raw/fares.parquet` in `INPUT_DIR`):
  - **Booking-class level:** each class gets a level, the share of passengers in cheaper classes, which makes up 30% of the fare value.
  - **Sold connections:** the only X/SHJ/Y connections rebooking may offer as two-flight itineraries through the hub.
- **Crew roster** (`parquet/crew/crew.parquet` in `INPUT_DIR`):
  - Copied without crew names into `raw/crew.parquet`; the operating data keeps only per-flight counts and headroom, no crew IDs.
  - **Headroom** = maximum FDP − planned FDP of the tightest crew member on the flight (`crew_flights.parquet`). Flights without a roster use the 10th percentile of the same flight number's history (`crew_fdp_estimates.parquet`, labelled estimated).
  - Every recovery option checks each delayed flight's delay against that headroom: under `CREW_TIGHT_MINUTES` (30) left is tight, past the maximum needs a reserve crew (`COST_RESERVE_CREW`, AED 15,000 per flight, assumed). The agent sees the result; the model page shows the FDP analysis (`GET /api/v1/crew/fdp`).
- **Loyalty, modelled on the airline's loyalty sample:**
  - Membership is the real booking flag.
  - Tiers are Basic, Silver, Gold and Platinum, with recovery priority Lowest, Low, Medium and High.
  - Each member gets a synthetic loyalty ID and points.
  - Bookings travelling with children or infants form family accounts; family members use the better of their own tier and the head of family's tier.
  - Rules: `LOYALTY_*` in `backend/app/ingest/build.py` and `backend/app/engine/priority.py`. The data quality report is in `<data>/ops/ingest_report.json`.

## Tests
```bash
scripts/check.sh                 # backend lint, format, strict types, 99 tests (26 of them use Testcontainers PostgreSQL); frontend type check, 24 tests, build
scripts/e2e.sh                   # Playwright end-to-end tests against the running stack (E2E_BASE_URL to target a server)
scripts/smoke.sh [base-url]      # post-deployment smoke test against a running stack (read-mostly)
scripts/check.sh lock            # after editing dependencies: refresh uv.lock / package-lock.json
```
Logs are written to `logs/`.

## Endpoints (through the web container)
| Path | Purpose |
|---|---|
| `/` | React app (sign in with a `DEMO_USERS` account) |
| `/api/v1/auth/login` | Sign in (rate limited: 10 per minute per address) |
| `/api/v1/meta`, `/api/v1/presets`, `/api/v1/flights` | Context, suggested scenarios, flight search |
| `/api/v1/scenarios` (+ `/{id}`, `/reprioritise`, `/select`, `/decisions`, `/messages`) | Run and store analyses, what-if, show another option, approvals and overrides, message drafts |
| `/api/v1/risk/watchlist` | Flights in the next 1–7 days by risk band, ranked by expected missed connections or by delay risk (read-only) |
| `/api/v1/risk/flights/{flight_id}` | One flight's delay risk and reasons, with its connecting passengers ranked by missed-connection risk |
| `/api/v1/risk/model` | Model card: training data, features, test metrics against the baseline |
| `/api/v1/risk/cascade` | The last month's cascade check: the knock-on formula against real departures, with all pairs (read-only) |
| `/api/v1/scenarios/{id}/rewards` | Goodwill reward plan for the passengers of the scenario's flight within a budget (phase 5, [design](docs/architecture/REWARDS_DESIGN.md)); computed on request, approved through `/decisions` |
| `/api/v1/risk/model-docs`, `/api/v1/risk/reward-model` | Evaluator only: the model comparison and tuning write-ups and the reward model card shown in the Model Card view |
| `/api/v1/test-data` (+ `/spec`) | Evaluator test data: file description, check, add and remove a few flights with their passengers ([ADR 0013](docs/architecture/adr/0013-test-data-upload.md) (`docs/architecture/adr/0013-test-data-upload.md`)) |
| `/api/v1/scenarios/{id}/strategy` | Switch a delay scenario's strategy (lowest cost, protect passengers, least delay); the recommendation follows (phase 3) |
| `/api/v1/agent/runs` (+ `/{id}`) | Start an agent run on a flight and follow its steps; the result is saved as a scenario for approval (phase 3, [agent card](docs/testing/agent-card.md)) |
| `/api/openapi.json`, `/api/docs` | OpenAPI schema and Swagger UI |
| `/healthz`; API `/health/live`, `/health/ready` | Health (readiness = database + operating data loaded) |

## Configuration
Everything is set in **`settings.env`** (template: `settings.env.example`). Docker Compose reads it through the link `.env`, because Compose only looks for a file with that name.
- **Data and access:** `INPUT_DIR`, `DEMO_USERS` (roles `OCC`, `PCU`, `EVALUATOR`; PCU has the same access as OCC; only the evaluator sees the Model Card and Test data views; see [Roles](#roles)), `TOKEN_SECRET`, `ANTHROPIC_API_KEY`, `AI_MODEL`.
- **Agent (phase 3):** `AGENT_EFFORT` (default `medium`), `AGENT_MAX_TOOL_CALLS` (12), `AGENT_TIMEOUT_SECONDS` (120). Without `ANTHROPIC_API_KEY` the rule-based planner answers every agent run.
- **Rule and cost defaults:** `MIN_TURN_MINUTES`, `DEFAULT_MCT_MINUTES`, `REBOOKING_WINDOW_HOURS`, `COST_DELAY_PER_MINUTE`, `COST_HOTEL_PER_NIGHT`, `COST_MEAL_VOUCHER`, `COST_REBOOKING_HANDLING`, `NOW_UTC` (demo clock).

## Push to your own git repository
```bash
git init && git add . && git commit -m "Disruption Advisor MVP"
git remote add origin <your-repo-url> && git push -u origin main
```
`settings.env`, the `.env` link, data and build output are git-ignored. Check `git status` before the first push.

## Data for analysis (optional)
After the ingest, inside the api container or a local backend environment:
- `python -m app.backtest`: replays real 2026 delays through the engine (`ops/backtest_report.json`, see docs/testing/backtest.md).
- `python -m app.ingest.share`: copies the name-free bookings (Oct 2025 - Mar 2027, by departure month) with a README to `DATA_DIR/share/` (about 950 MB). Share it through a drive, never Git.
