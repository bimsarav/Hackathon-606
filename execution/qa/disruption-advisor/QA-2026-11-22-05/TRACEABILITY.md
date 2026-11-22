# Traceability – QA-2026-11-22-05 (disruption-advisor, production regression after deployment)

Environment: production, UI http://92.5.154.198:8080 (API through the UI proxy `/api/v1`), Chrome via Claude in Chrome, desktop viewport ~1568 px, 2026-11-22. Release: production 2026-11-22 (served bundle `index-CkVpRpVr.js`), containing the fixes from cycles QA-2026-11-22-01…04 and Judge fixes J-DA-004, 009–013, 015, 016.
Sources: cycle brief, `instructions/QA_RULES.md`, `DEFECTS.md`, reports of cycles 01–04; source code read only to understand expected behaviour (`frontend/src/Shared.tsx`, `styles.css`, `App.tsx`, `backend/app/auth.py`).
Accounts: OCC, EVALUATOR, PCU, each signed in by the user in the given tab; QA typed no credentials. The tab was reloaded once at the start of each role.
Records created on production: delay analysis G9519 21 Nov +120 (scenario 2f5e9f27…, occ) with 2 strategy switches, 1 reward plan at AED 5,000 (not approved), 1 AI message draft; cancellation analysis G9298 20 Nov (scenario dcb0f466…, occ) with 2 priority-weight re-runs (changed, then reset). Two option selections on scenario 2f5e9f27… (POST /select: cancel G9294/G9295, then back to the recommended A6-ARI), made before the coordinator's read-only rule; final state = recommended option. No approvals, rejections, uploads, flight edits, settings changes, new agent runs or browser dialogs.
Raw notes: `OCC-NOTES.md` (all three roles). Screenshots: `screenshots/`.

| ID | Feature / check | Source | Steps (summary) | Expected | Actual | Status | Defect |
|---|---|---|---|---|---|---|---|
| O-01 | OCC menu | J-DA-011, brief | Sign-in as OCC, read sidebar | 5 items incl. "Predict the Flight Delay (AI agent)" | 5 items as expected (no Model Card / Test data) | PASS | |
| O-02 | Watchlist without risk/model, cascade panel | J-DA-009, brief | Open Delay Watchlist, read network, open "Expand the full view" | No risk/model call; cascade figures and full view | Only risk/cascade + risk/watchlist (200); 1,656 pairs, full view with charts (occ-01) | PASS | |
| O-03 | G9519 21 Nov +120 tiles | brief | Flight Delay → G9519 → 21 Nov, delay 120 | Tiles consistent | Swap A6-ARI over G9294 · 2 h · 29 of 153 · AED 66,275 (occ-02) | PASS | |
| O-04 | Flight Board | brief | Expand Flight Board | Before/after boards | 2 aircraft, swapped legs shown before/after | PASS | |
| O-05 | 6 options + recommendation | brief | Read Recovery options | 6 options, recommended marked | 6 options, recommended = Selected | PASS | |
| O-06 | Strategies switch | brief | Strategies compared → Protect passengers → back to Lowest cost | Active strategy and recommendation follow | Switches both ways; tie between 2 swaps explained in Why? | PASS | |
| O-07 | Why? wording | J-DA-010 | Read Why? | Plain language, engine numbers, AI attribution | As expected | PASS | |
| O-08 | Crew tile vs section | J-DA-012 | Compare tile and section (G9519; G9406) | Same status | "within limits" both; G9406 "tight" both | PASS | |
| O-09 | People boxes | brief | Open/close the 3 passenger boxes | Each opens its detail | As expected | PASS | |
| O-10 | Hotel label | brief | Rebooking box | Label explains hotel count | "27 hotel rooms (no seat, or long or overnight wait)" | PASS | |
| O-11 | Reward plan AED 5,000 + list vs booked note | J-DA-013, brief | Rewards → budget 5000 → Recommend rewards | Spend ≤ budget; note on 165 vs 163 | 4,990 of 5,000; 55 of 165; note shown; chip totals = 4,990 (occ-03); not approved | PASS | |
| O-12 | AI message draft, UTC | brief | Rebooking → row 1 Details → Personalise with AI | Readable time with UTC | "departing 21 Nov 17:45 UTC" (occ-04) | PASS | |
| O-13 | Cancellation G9298 20 Nov tiles | brief | Cancellation → G9298 → 20 Nov | Consistent tiles | 12 / 12 / 164 / 164 / AED 106,680 (occ-05) | PASS | |
| O-14 | Split bookings count vs list | QA-DA-002 | Show all 176, group by booking | Tile = box = bookings with mixed outcomes | 2 = 2 = 2 (61C15M 3/34, 601TQ8 9/32) | PASS | |
| O-15 | Three boxes | brief | Open rebooking, seats, rewards boxes | Each opens | Alternative flight G9294 12/12, solver optimal | PASS | |
| O-16 | Weights re-run | brief | Loyalty 20→45, re-run; reset, re-run | Order changes, reset restores | 9 of first 30 positions change; reset restores | PASS | |
| O-17 | Recent chips | QA-DA-003 | Read chips, reopen G9519 +120 | Flight day, one per flight/type/delay, reopen | As expected, no duplicate | PASS | |
| O-18 | Recent Searches | J-DA-012 | Open page, reopen G9406 | Date, delay, run time; reopen | As expected (occ-06) | PASS | |
| O-19 | Agent page, existing run | J-DA-011 | Open run G9901 22 Nov | No internal phase label | 0 "phase" matches; steps and recommendation shown (occ-07) | PASS | |
| O-20 | Views open at top | J-DA-012 | Open delay, cancellation, recent, agent views | scrollY 0 | As expected | PASS | |
| O-21 | No Model Card / Test data for OCC | brief | Menu + page text | Absent | Absent | PASS | |
| O-22 | Console/network clean | brief | Read console and /api requests | No errors, no 4xx | All 200/201, no console errors | PASS | |
| O-23 | Day filter chips | regression (launcher) | G9519 → Sat 21, hover the selected chip | Label stays readable | Label invisible on hover (white on light grey) (occ-08) | FAIL | QA-DA-007 |
| E-01 | EVALUATOR menu | brief | Read sidebar | 7 items | 7 items | PASS | |
| E-02 | Model Card hub | brief | Open Model Card | Overview boxes | 9 boxes with headline figures (eval-01) | PASS | |
| E-03 | Model Card detail pages | brief | Open each of 9 "Open details" | Each opens at top, no errors | All 9 open, breadcrumb, at top, all GET 200 | PASS | |
| E-04 | Test data page (read only) | brief | Open Test data | Options and specs; nothing changed | As expected, no test data loaded (eval-02) | PASS | |
| E-05 | Watchlist model-quality panel | brief | Watchlist → "How good are these predictions?" | risk/model 200, figures | 200; AUC +60 0.77 vs 0.68 (= Model Card 0.770); confusion rows sum 5,956 (eval-03, eval-04) | PASS | |
| E-06 | One delay view | brief | Reopen G9519 +120 from Recent chip | Same figures as OCC | Same; GET only (eval-05) | PASS | |
| E-07 | Console/network | brief | Read console and /api | No errors | All 200, no console errors | PASS | |
| P-01 | Sign-in subtitle | QA-DA-004 | Read served bundle (sign-in page not reachable without sign-out) | "OCC, PCU and evaluators" | String present in served bundle | PASS | |
| P-02 | PCU menu | brief | Read sidebar | 5 items | 5 items (pcu-01) | PASS | |
| P-03 | One delay analysis | brief | Reopen G9519 +120 from Recent chip | Figures shown, read only | Same figures, crew tile = section, 6 options (pcu-02) | PASS | |
| P-04 | No Model Card / Test data | brief | Menu + page text | Absent | Absent | PASS | |
| P-05 | API 403 for evaluator endpoints | brief | fetch GET with page session | 403 on evaluator endpoints, 200 on shared ones | 6 × 403 ("This view is for the evaluator role"); cascade, watchlist, meta 200 | PASS | |
| P-06 | No 4xx in normal use | J-DA-009 | Watchlist as PCU | No risk/model call | cascade + watchlist only (200) | PASS | |
| K-01 | Known limitation QA-DA-005 | DEFECTS | G9519 + Sat 21 | (not re-reported) | Still present: "1 FLIGHTS MATCH" | NOT APPLICABLE | QA-DA-005 |
| K-02 | Known limitation QA-DA-006 | DEFECTS | G9298 list | (not re-reported) | Still present: marker on 12 seated only | NOT APPLICABLE | QA-DA-006 |
