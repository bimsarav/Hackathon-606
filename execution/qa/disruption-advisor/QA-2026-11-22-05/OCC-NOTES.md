# QA-2026-11-22-05 · raw notes · OCC (production, signed in by the user)

Tab reloaded once at start. Chrome desktop 1568 px. No approvals, rejections, uploads, edits, settings, new agent runs.

| # | Check | Result | Evidence / note |
|---|---|---|---|
| O-01 | Menu 5 items incl. "Predict the Flight Delay (AI agent)" | PASS | Flight Delay, Cancellation, Predict the Flight Delay (AI agent), Delay Watchlist, Recent Searches |
| O-02 | Watchlist: no risk/model call; cascade panel | PASS | calls: risk/cascade 200, risk/watchlist 200 only; 1,656 pairs, full view opens (occ-01) |
| O-03 | G9519 21 Nov +120 tiles | PASS | Swap A6-ARI over G9294 · 2 h · 29 of 153 · AED 66,275 (occ-02) |
| O-04 | Flight Board | PASS | before/after boards, 2 aircraft, swap legs moved |
| O-05 | 6 options + recommendation | PASS | 6 rows, recommended = Selected |
| O-06 | Strategies switch | PASS | Protect passengers -> A6-ANO, Why re-worded; back to Lowest cost. Tie (same figures) explained in Why |
| O-07 | Why? wording | PASS | plain language, "Text written by claude-opus-5-5" |
| O-08 | Crew tile vs section | PASS | within limits / 1 flight(s), estimated duty both; G9406: tight / tightest 3 min left both |
| O-09 | People boxes | PASS | missed-connection, rebooking, rewards boxes open/close |
| O-10 | Hotel label | PASS | "27 hotel rooms (no seat, or long or overnight wait)" |
| O-11 | Reward plan AED 5,000 + list vs booked note | PASS | spend 4,990 (left 10); 55 of 165 on passenger list; note "inventory count says 163 booked..."; chip totals sum to 4,990 (occ-03). Not approved |
| O-12 | AI message draft, readable UTC | PASS | "departing 21 Nov 17:45 UTC" (occ-04) |
| O-13 | Cancellation G9298 20 Nov tiles | PASS | 12 free seats, 12 protected, 164 hotel, 164 no seat, AED 106,680 (occ-05) |
| O-14 | "booking(s) could not stay together" vs list | PASS | tile 2 = box 2 = list (61C15M 3/34 seated, 601TQ8 9/32 seated) |
| O-15 | Three boxes | PASS | rebooking, alternative flights (G9294 12/12, solver optimal), rewards |
| O-16 | Weights re-run | PASS | loyalty 20->45 re-run: 9 of first 30 positions change; reset + re-run restores |
| O-17 | Recent chips | PASS | flight day shown, one per flight/type/delay, G9519 +120 reopened, no duplicate chip |
| O-18 | Recent Searches | PASS | type, flight, date, delay, run time; G9406 reopened (occ-06) |
| O-19 | Agent page, existing run, no phase label | PASS | G9901 run opened, 0 "phase" matches (occ-07) |
| O-20 | Each view opens at top | PASS | delay, cancellation, recent, agent |
| O-21 | No Model Card / Test data | PASS | not in menu or page text |
| O-22 | Console/network clean | PASS | all /api calls 200/201; no console errors (console tracking started after first load) |
| O-23 | Day filter chips (incidental) | FAIL | QA-DA-007: selected chip label invisible on hover (occ-08) |

Known limitations still present: QA-DA-005 ("1 FLIGHTS MATCH "G9519"" with Sat 21 filter); QA-DA-006 (group split marker on 12 seated travellers only).

Observations (not bugs): agent run step text shows raw ids "swap:A6-AOH (protect_passengers)"; viewing an option posts /select (selection restored to the recommended option afterwards).

OCC: 22/23 passed (95.7 %).

## Process note (coordinator rule after OCC)
During OCC, "Select" on two recovery options of G9519 (cancel G9294/G9295, then back to A6-ARI) sent POST /scenarios/2f5e9f27…/select twice; the selection ends on the recommended option. From EVALUATOR on, no Select or other state-saving control is used.

# EVALUATOR (production, signed in by the user; tab reloaded at start)

| # | Check | Result | Evidence / note |
|---|---|---|---|
| E-01 | 7 menu items | PASS | Flight Delay, Cancellation, Predict the Flight Delay (AI agent), Delay Watchlist, Model Card, Test data, Recent Searches |
| E-02 | Model Card hub | PASS | 9 boxes (3 models, 5 rules/optimiser/AI, uploaded test flights) (eval-01) |
| E-03 | Model Card detail pages | PASS | all 9 open via "Open details", breadcrumb "All models / …", open at top, charts present on 6, no error text; all GET 200 (risk/model, model-docs, reward-model, cascade, crew/fdp, meta, test-data) |
| E-04 | Test data page (read only) | PASS | two options, "No test data is loaded", column specs; GET test-data/spec, test-data 200; nothing uploaded or edited (eval-02) |
| E-05 | Watchlist model-quality panel | PASS | GET risk/model 200; "How good are these predictions?" AUC +60 0.77 vs 0.68 (matches Model Card 0.770); confusion rows sum to 5,956 test flights (eval-03, eval-04) |
| E-06 | One delay view | PASS | G9519 21 Nov +120 reopened from Recent chip (GET only): same tiles as OCC, crew tile = section, 6 options (eval-05) |
| E-07 | Console/network | PASS | no console errors; all API calls 200 |

EVALUATOR: 7/7 passed.

# PCU (production, signed in by the user; tab reloaded at start; read-only)

| # | Check | Result | Evidence / note |
|---|---|---|---|
| P-01 | Sign-in subtitle | PASS (bundle) | sign-in page not viewable without signing out; served bundle index-CkVpRpVr.js contains "Disruption recovery for OCC, PCU and evaluators" |
| P-02 | Menu 5 items | PASS | Flight Delay, Cancellation, Predict the Flight Delay (AI agent), Delay Watchlist, Recent Searches (pcu-01) |
| P-03 | One delay analysis | PASS | G9519 21 Nov +120 reopened from Recent chip (GET only): same tiles, crew tile = section, 6 options, opens at top (pcu-02) |
| P-04 | No Model Card / Test data in UI | PASS | not in menu or page text |
| P-05 | API 403 for evaluator endpoints | PASS | fetch with page session: risk/model, risk/model-docs, risk/reward-model, test-data, test-data/spec, test-data/edits -> 403 "This view is for the evaluator role"; controls cascade, watchlist, meta -> 200 |
| P-06 | No 4xx in normal use | PASS | Watchlist as PCU calls only cascade + watchlist (200), no risk/model; no console errors |

PCU: 6/6 passed.
