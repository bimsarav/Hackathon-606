# Disruption Advisor System Architecture

Disruption Advisor helps an airline's **Operations Control Centre (OCC)** and **Passenger Control Unit (PCU)** handle a flight disruption before it cascades. For a delayed or cancelled flight, it:
1. Finds every downstream flight on the same aircraft rotation and every passenger whose journey breaks, over the next 7 days.
2. Compares recovery options (MVP: absorb the delay, or swap in a same-type aircraft) on delay, passengers affected and cost.
3. Ranks the affected passengers with transparent, configurable priority tiers and weights.
4. Assigns them to alternative flights within real seat inventory.
5. Explains every recommendation and drafts the passenger messages.

It **recommends only**: a person approves or rejects every action (requirement UC5, decision Q21).

Requirement sources: the UC5 use-case document (`Disruption_Management_UC5.docx`), the briefing transcript, the product-owner Q&A of 2026-11-20 and the clarification register (Q1–Q30). Domain background comes from the team's airline knowledge base (disruption management topic), which is not part of this repository.

## 1. System context
```mermaid
flowchart LR
  occ([OCC controller]) -->|assess delay, compare and approve recovery| DA
  pcu([PCU agent]) -->|prioritise and rebook passengers, approve messages| DA
  DA[Disruption Advisor]
  files[(Airline extracts<br/>bookings, schedule, rotation,<br/>inventory, MCT, punctuality)] -->|batch ingest| DA
  tz[(Public airport<br/>time-zone dataset)] -->|ingest| DA
  DA -->|explain + draft English messages<br/>minimised fields, no contact details| llm[Anthropic Claude API]
  DA -.->|later phases: events, real SSR/loyalty,<br/>crew, PSS write-back| ext[Airline systems]
```

## 2. Containers (Docker Compose)
```mermaid
flowchart LR
  browser([Browser]) -->|HTTP :8888 MVP<br/>HTTPS later| web
  subgraph host [Server: Docker Compose, restart unless-stopped]
    web[web<br/>nginx: React SPA + /api proxy<br/>CSP, security headers]
    api[api<br/>FastAPI + uvicorn<br/>impact, recovery, priority,<br/>rebooking, explanations]
    ingest[ingest<br/>one-shot: extracts → ops.duckdb<br/>runs when data changes]
    migrate[migrate<br/>one-shot: alembic upgrade head]
    db[(PostgreSQL 18<br/>scenarios, recommendations,<br/>decisions, weight profiles, audit)]
    ops[(ops.duckdb volume<br/>read-only analytics store)]
    input[/input files<br/>read-only mount/]
  end
  web -->|/api/| api
  api -->|SQLAlchemy| db
  api -->|DuckDB read-only| ops
  ingest --> ops
  input --> ingest
  migrate --> db
  api -->|HTTPS| claude[Claude API]
```
- **Two stores, each for what it does best.** DuckDB holds the large, read-mostly airline extracts: 27.9M booking rows reduced to the operating window and aggregates. PostgreSQL holds what users create (scenarios, decisions, audit), with migrations and backups.
- **The ingest job** turns the raw extracts into clean, typed tables. It applies the data rules (UTC/local time, active bookings, curtail/oversell capacity) and records every mismatch instead of failing (PO Q&A).

## 3. Components inside the API
```mermaid
flowchart TB
  subgraph api [api: modular monolith]
    auth[auth<br/>demo roles OCC / PCU]
    scen[scenarios<br/>create disruption: delay or cancellation]
    net[network<br/>rotation graph, turn times,<br/>delay propagation, 7-day cascade]
    pax[passengers<br/>journeys, connections, MCT 15 min–20 h,<br/>misconnect detection]
    rec[recovery<br/>options: delay · same-type swap<br/>cost and impact scoring]
    pri[priority<br/>tiers + weighted score + reasons]
    reb[rebooking<br/>CP-SAT seat assignment<br/>groups kept together]
    exp[explain<br/>Claude or template narrative,<br/>message drafts]
    dec[decisions<br/>approve / reject, audit trail]
  end
  scen --> net --> pax
  net --> rec
  pax --> rec
  rec --> exp
  pax --> pri --> reb --> exp
  exp --> dec
```
| Module | Owns | Key rule sources |
|---|---|---|
| `network` | Flight legs, tails, minimum turn time, downstream propagation | Rotation file; turn-time defaults per type (configurable) |
| `passengers` | Journeys built from active segments; connections at SHJ | MCT table; connection window 15 min–20 h (Q8) |
| `recovery` | Recovery options and their KPIs: delay min, pax affected, misconnects, cost | Cost defaults (Q15, configurable) |
| `priority` | Strict tiers then weighted score, with per-attribute contributions | Rule defaults Q12 (synthetic README) |
| `rebooking` | Alternative flights and seat assignment | Inventory allocation incl. curtail/oversell (Q10, PO) |
| `explain` | Natural-language reasons and English message drafts | Claude API; deterministic templates as fallback (Q26) |
| `decisions` | Approvals, rejections, who/when/what | Human-in-the-loop (Q21) |

## 4. Data flow and model
```mermaid
flowchart LR
  B[Booking CSVs ×18<br/>27.9M rows] --> C1[clean: Latin-1 → UTF-8,<br/>reject malformed lines]
  C1 --> C2[active segments<br/>CNF/CNF/ACT, window 19–30 Nov]
  R[Rotation .xls] --> L[flight legs + tails]
  I[Inventory CSV] --> S[seat capacity per flight<br/>adult_capacity ± curtail/oversell]
  M[Connection times] --> J
  T[Airport time zones] --> L
  SYN[Synthetic enrichment<br/>profiles · fare families · SSR · registry] --> C2
  C2 --> J[journeys + connections]
  L --> J
  S --> AV[availability = capacity − booked<br/>mismatch flagged, never fatal]
  C2 --> AV
  J --> OPS[(ops.duckdb)]
  L --> OPS
  AV --> OPS
```
```mermaid
erDiagram
  FLIGHT_LEG ||--o{ PAX_SEGMENT : carries
  TAIL ||--o{ FLIGHT_LEG : "operates (rotation order)"
  FLIGHT_LEG ||--|| SEAT_AVAILABILITY : has
  PNR ||--o{ PASSENGER : contains
  PASSENGER ||--o{ PAX_SEGMENT : books
  PASSENGER }o--|| CUSTOMER_PROFILE : "matched by customer_key"
  PAX_SEGMENT }o--|| BOOKING_CLASS : "fare family / revenue type"
  PASSENGER ||--o{ SSR : "special needs (synthetic)"
  SCENARIO ||--o{ RECOMMENDATION : produces
  RECOMMENDATION ||--o{ REBOOKING_LINE : "passenger → new flight"
  RECOMMENDATION ||--o{ DECISION : "approved / rejected by"
  FLIGHT_LEG {
    string flight_no "G9xxx"
    string tail
    ts std_utc
    ts sta_utc
    string dep
    string arr
    string model
  }
  SEAT_AVAILABILITY {
    int capacity
    int booked
    int available
    bool synthetic
    bool mismatch
  }
  PAX_SEGMENT {
    string pnr
    string customer_key
    string flight_no
    ts dep_utc
    string booking_code
    float fare
    float ancillaries
  }
  CUSTOMER_PROFILE {
    string customer_key
    string tier_synthetic
    int flown_12m
    string frequency_band
  }
  SCENARIO {
    uuid id
    string type "DELAY or CANCEL"
    string flight_no
    int delay_min
    ts created_at
    string created_by
  }
  DECISION {
    uuid id
    string action "APPROVE or REJECT"
    string user
    ts at
    string comment
  }
```
ops.duckdb holds the `FLIGHT_LEG` … `SSR` entities and is rebuilt by `ingest`. PostgreSQL holds `SCENARIO`, `RECOMMENDATION`, `REBOOKING_LINE`, `DECISION` and weight profiles.

## 5. Scenario A: inbound delay at the hub (delay vs aircraft swap)
```mermaid
sequenceDiagram
  actor OCC as OCC controller
  participant UI as Web UI
  participant API as api
  participant NET as network
  participant PAX as passengers
  participant REC as recovery
  participant EXP as explain (Claude / template)
  OCC->>UI: G9xxx into SHJ delayed 150 min
  UI->>API: POST /scenarios {flight, delay}
  API->>NET: propagate along tail rotation (turn times, slack)
  NET-->>API: downstream legs + new ETDs (7-day horizon)
  API->>PAX: re-check every connection (MCT, 15 min–20 h)
  PAX-->>API: misconnecting passengers, by journey
  API->>REC: options = absorb delay | swap with each same-type tail free at SHJ
  REC-->>API: per option: delay min, pax affected, misconnects, cost
  API->>EXP: best option + trade-offs
  EXP-->>API: explanation ("why this, why not the others")
  API-->>UI: impact view, ranked options, recommendation
  OCC->>UI: approve or reject (audited)
```

## 6. Scenario B: cancellation with too few seats (priority + rebooking)
```mermaid
sequenceDiagram
  actor PCU as PCU agent
  participant UI as Web UI
  participant API as api
  participant PRI as priority
  participant REB as rebooking (CP-SAT)
  participant EXP as explain
  PCU->>UI: G9yyy cancelled
  UI->>API: POST /scenarios {flight, CANCEL}
  API->>PRI: affected passengers + attributes
  PRI-->>API: tier + score + contribution per attribute
  API->>REB: alternatives (same O&D or legal SHJ connection, ≤24 h), seats, priority
  REB-->>API: assignment (groups together), unprotected passengers → next day + hotel
  API->>EXP: reasons per passenger + message drafts
  API-->>UI: priority list, rebooking plan, messages
  PCU->>UI: change weights → re-run (what-if)
  PCU->>UI: approve plan / messages (audited)
```

## 7. Priority decision logic
```mermaid
flowchart TB
  A[Affected passenger] --> F{Feasible alternative?<br/>seats, MCT, same PNR group}
  F -- no --> NX[Next day + hotel + meals<br/>EU261 care if departing EU]
  F -- yes --> T1{Tier 1: mandated care<br/>WCHR/WCHS/WCHC, BLND, DEAF, MEDA,<br/>PREG, UMNR, infant in PNR}
  T1 -- yes --> P1[Priority band 1]
  T1 -- no --> T2{Tier 2: urgency<br/>onward connection, last flight of day,<br/>long journey}
  T2 -- yes --> P2[Priority band 2]
  T2 -- no --> P3[Priority band 3]
  P1 & P2 & P3 --> W[Weighted score inside the band<br/>loyalty tier · frequency · fare value ·<br/>ancillaries · journey complexity · group/family]
  W --> NR{Non-revenue?}
  NR -- yes --> L[After all revenue passengers]
  NR -- no --> O[Ordered list + reasons]
```
The commercial score never moves a passenger across a legal or care tier (UC5: "respect passenger rights … independently of commercial scores").

## 8. Deployment
```mermaid
flowchart LR
  user([OCC / PCU users]) -->|http://92.5.154.198:8888 MVP| fw
  subgraph oci [OCI VM eu-frankfurt-1: 8 vCPU, 62 GiB, Oracle Linux 10]
    fw[firewalld: 22, 80, 443, 8080, 8888, 5432 open]
    fw --> web
    subgraph compose [docker compose, restart unless-stopped, docker enabled at boot]
      web --> api
      api --> db[(postgres volume)]
      api --> ops[(ops.duckdb volume)]
      ingest --> ops
    end
    data[/~/disruption-advisor/input<br/>airline extracts, read-only/]
    data --> ingest
    secrets[/.env on server only<br/>DB password, AI key, user passwords/]
  end
  api -->|HTTPS| claude[Claude API]
```
- PostgreSQL is **not** published on 5432; only `web` is published.
- Secrets live only in the server's `.env` (mode 600), never in git.
- The incremental plan (MVP, then the later phases, each needing approval) is in [../delivery/MVP_AND_INCREMENTAL_PLAN.md](../delivery/MVP_AND_INCREMENTAL_PLAN.md).

## 9. Cross-cutting concerns
- **Security:**
  - Login with two demo roles (OCC, PCU); credentials come from server secrets (ADR 0004).
  - Strict input validation; RFC 9457 errors; CSP and security headers at nginx; non-root containers.
  - Passenger data is treated as real (Q3): no names or contact details go to the LLM, only the minimum fields per message.
- **Explainability:** every option, score and assignment carries machine-readable reasons (attribute contributions, binding constraints), which the UI shows. The LLM only rewrites these into prose and never decides.
- **Robustness:** booking vs inventory mismatches are flagged and the run continues (PO Q&A). Synthetic values are labelled in the UI.
- **Observability:** JSON logs with request id; `/health/live` and `/health/ready` (PostgreSQL and ops store); container healthchecks.
- **Time:** all logic runs in UTC; local times come from the airport time-zone table (Q9, Q22).
- **Limits (MVP):** no crew legality (no crew data), no equipment change, no bus legs, simulated "now" = 2026-11-20 (Q2).
