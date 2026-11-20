# Disruption Advisor

Disruption Advisor helps an airline's Operations Control Centre (OCC) and Passenger Control Unit (PCU) handle a flight disruption before it cascades.
- **Scenario A, delay:** for a delayed flight it shows every later flight on the same aircraft rotation and every passenger connection that breaks over the next 7 days. It compares recovery options (absorb the delay, or swap in a same-type aircraft) on delay, missed connections and cost, and recommends one.
- **Scenario B, cancellation:** for a cancelled flight it ranks the affected passengers. Strict tiers come first (mandated care, then urgency); configurable weights order passengers inside a tier (loyalty, travel frequency, fare, ancillaries, journey, family/group). It then assigns passengers to alternative flights within the seats actually available, keeping bookings together.
- **Explanations:** every recommendation is explained in plain English, written by Claude when an API key is configured, otherwise by templates, and passenger messages are drafted.
- **Human approval:** the tool **only recommends**. A person approves or rejects every action, and each decision is audited.

Stack: Python 3.14 · FastAPI · DuckDB over Parquet · Google OR-Tools (CP-SAT) · Anthropic Claude API · SQLAlchemy 2 · Alembic · PostgreSQL 18 · React 19 + TypeScript + Vite · nginx · Docker Compose · Playwright.
Details: [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) (diagrams) · [docs/delivery/MVP_AND_INCREMENTAL_PLAN.md](docs/delivery/MVP_AND_INCREMENTAL_PLAN.md) · [docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md).

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
Then open `http://localhost:${WEB_PORT}`. The API docs are at `/api/docs`.

Start-up runs in this order:
1. `db`
2. `migrate` (Alembic)
3. `ingest`: converts the extracts to typed Parquet. It takes about 4 minutes the first time, and skips the work when the inputs are unchanged.
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
- **Synthetic fields:** the extracts have no loyalty tier, fare family or special-service codes, so these are synthetic, deterministic and labelled in the UI. The data quality report is in `<data>/ops/ingest_report.json`.

## Tests
```bash
scripts/check.sh                 # backend lint, format, strict types, 39 tests (Testcontainers PostgreSQL); frontend type check, tests, build
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
| `/api/v1/scenarios` (+ `/{id}`, `/reprioritise`, `/decisions`, `/messages`) | Run and store analyses, what-if, approvals, message drafts |
| `/api/openapi.json`, `/api/docs` | OpenAPI schema and Swagger UI |
| `/healthz`; API `/health/live`, `/health/ready` | Health (readiness = database + operating data loaded) |

## Configuration
Everything is set in **`settings.env`** (template: `settings.env.example`). Docker Compose reads it through the link `.env`, because Compose only looks for a file with that name.
- **Data and access:** `INPUT_DIR`, `DEMO_USERS`, `TOKEN_SECRET`, `ANTHROPIC_API_KEY`, `AI_MODEL`.
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
