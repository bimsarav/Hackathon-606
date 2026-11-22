# Defect log – disruption-advisor (QA-DA-nnn)

| Bug ID | Title | Feature | Severity | Priority | Status | Found in | Retested in |
|---|---|---|---|---|---|---|---|
| QA-DA-001 | Delivered solution-design PDF still names the developer's git branch (HTML source fixed, PDF not regenerated) | Delivery docs (J-DA-015) | Low | P2 | Closed (verified fixed) | QA-2026-11-22-01 | QA-2026-11-22-02 |
| QA-DA-002 | Cancellation "booking(s) split" shows a passenger count (90) larger than the protected passengers (12) | Cancellation analysis – tiles / rebooking box | Low | P3 | Closed (verified fixed in retest 2) | QA-2026-11-22-01 | QA-2026-11-22-03, QA-2026-11-22-04 |
| QA-DA-003 | Launcher "Recent" chips have identical labels (e.g. "G9901 · +150m" ×3), not distinguishable | Search launcher – Recent chips | Low | P4 | Closed (verified fixed) | QA-2026-11-22-01 | QA-2026-11-22-03 |
| QA-DA-004 | Sign-in page subtitle names only "OCC and PCU" although the evaluator role signs in on the same page | Sign-in page | Low | P4 | Closed (verified fixed) | QA-2026-11-22-02 | QA-2026-11-22-03 |
| QA-DA-005 | Launcher search header uses the plural for one result: "1 FLIGHTS MATCH" | Search launcher – results header | Low | P4 | Known limitation (user 2026-11-22: do not fix) | QA-2026-11-22-03 | — |
| QA-DA-006 | "group split" marker shown only on travellers with a seat; travellers of the same split booking without a seat are not marked | Cancellation analysis – passenger list | Low | P4 | Known limitation (user 2026-11-22: do not fix) | QA-2026-11-22-04 | — |
| QA-DA-007 | Selected day chip label disappears on mouse hover (white text on light-grey background) | Search launcher – Day filter chips | Low | P4 | Open | QA-2026-11-22-05 | — |

## QA-DA-001 retest (QA-2026-11-22-02)
Verified fixed. `pdftotext` of `docs/delivery/aeroRecovery_Solution_Design.pdf` (rebuilt 2026-11-22 00:46 +04, 9 pages, A4) vs the committed copy at HEAD (9 pages): the only text difference is page 1 "Release of 21 November 2026 (git branch <developer name>)" → "Release of 21 November 2026". No developer or branch name in the PDF text or raw strings, nor anywhere in the product tree (grep, node_modules and .git excluded). HTML source `solution-design/index.html:61` carries the same "Release of 21 November 2026"; a word-level comparison of HTML vs PDF text differs only in CSS upper-casing.

## QA-DA-004 · Sign-in page subtitle names only "OCC and PCU"
- Feature: sign-in page · Release: local build 2026-11-22 (uncommitted tree, branch v1.0.0) · Environment: local http://localhost:8080, Chrome (Claude in Chrome).
- Description: the sign-in card says "Disruption recovery for OCC and PCU". The evaluator role now signs in on the same page (README role table lists OCC, Evaluator and PCU), so the line leaves out one of the three roles.
- Preconditions: signed out.
- Steps: open http://localhost:8080 signed out; read the line under "Sign in".
- Expected: wording that covers every role that signs in there (or no role list).
- Actual: "Disruption recovery for OCC and PCU" (screenshot `QA-2026-11-22-02/screenshots/signin-01-subtitle.png`).
- Reproducibility: always.
- Severity: Low (text only; no function affected) · Priority: P4.
- Impact: an evaluator may wonder whether the page is meant for them; cosmetic.
- Suspected area (suspicion): `frontend/src/App.tsx:183` static text.

## QA-DA-002 retest (QA-2026-11-22-03) – reopened
- Release: local build 2026-11-22 (uncommitted tree, v1.0.0) · Environment: local http://localhost:8080, Chrome · Account: OCC (also seen as EVALUATOR, PCU).
- Steps: Cancellation → suggested "G9298 SHJ→TBS · 20 Nov" (new run 21 Nov 20:57Z) → read the Protected tile and the "Passengers to rebook" box → Open details → "Show all 176 passengers".
- Expected: the number counts bookings whose travellers could not stay together, matching the bookings marked as split in the passenger list.
- Actual: wording fixed and the number is now bookings: tile "12 · 3 booking(s) could not stay together", box "3 bookings not kept together". The passenger list marks 2 bookings "group split" (party of 35: 3 seated on G9294, the rest without a seat; party of 33: 9 seated, the rest without a seat). The third counted booking (party of 24) has all 24 travellers "No seat within 24 h" with the same care offer and no split marker: they were not separated. Expected 2, shown 3.
- Evidence: screenshots `QA-2026-11-22-03/screenshots/occ-03-cancel-G9298-tiles.jpg`, `occ-04-cancel-rebooking-box.jpg`, `occ-05-cancel-list-group-split.jpg`, `occ-06-cancel-party24-no-split-marker.jpg`; scenario `GET /api/v1/scenarios/972f00e4-…` rows: 3 PNRs with `split=true` (90 rows), of which only 2 have travellers on different outcomes.
- Reproducibility: always (G9298 20 Nov).
- Severity: Low · Priority: P3 (summary figure overstates split bookings whenever a large group gets no seat at all).
- Suspected area (suspicion): `backend/app/engine/rebooking.py` sets `split=True` for every member of a PNR larger than the biggest free block before solving; `scenarios.py split_bookings()` counts those PNRs regardless of outcome. Counting PNRs whose members ended on different assigned flights (including none) would match the list.

## QA-DA-003 retest (QA-2026-11-22-03) – verified fixed
Chips read e.g. "G9406 21 Nov · +82m", "G9901 22 Nov · +69m", "G9298 20 Nov · Canc"; duplicates in history (G9519 +150 ×2, G9901 +150 ×2, G9298 Canc ×3–4) show one chip with the newest run; tooltip "G9406 · 21 Nov 23:25Z · delay 82 min · last run 21 Nov 18:04Z by occ"; chips reopen the right scenario (G9406 +82, G9805 21 Nov) on Flight Delay and Cancellation; same for EVALUATOR and PCU. Screenshots occ-02, occ-10, occ-11, eval-01, pcu-01.

## QA-DA-004 retest (QA-2026-11-22-03) – verified fixed
Sign-in card reads "Disruption recovery for OCC, PCU and evaluators" (screenshot signin-01-subtitle.png).

## QA-DA-005 · Launcher search header uses the plural for one result
- Feature: search launcher (Flight Delay page; same component on Cancellation) · Release: local build 2026-11-22 · Environment: local :8080, Chrome · Account: OCC.
- Steps: Flight Delay → type "G9148" → click day chip "Fri 20".
- Expected: "1 flight matches "G9148"" (singular), and a clear no-match wording for 0.
- Actual: "1 FLIGHTS MATCH "G9148""; for an unknown flight "0 FLIGHTS MATCH "G0000"".
- Reproducibility: always. Pre-existing (text unchanged by this fix round).
- Severity: Low (text only) · Priority: P4.
- Impact: cosmetic.
- Suspected area (suspicion): `frontend/src/Launcher.tsx:381` template `${n} flights match`.

## QA-DA-002 retest 2 (QA-2026-11-22-04) – verified fixed
- Release: local build 2026-11-22 (uncommitted, v1.0.0; API container recreated 02:26 +04, contains `split_pnrs()`) · Environment: local :8080, Chrome · Accounts: OCC, EVALUATOR.
- G9298 20 Nov, new run 21 Nov 22:27Z (scenario 4dd11d75…): tile "12 · 2 booking(s) could not stay together", box "2 bookings not kept together". Full list (176 rows, 27 bookings): bookings with travellers on different outcomes = 61C15M (party of 35: 3 on G9294, 31 no seat) and 601TQ8 (party of 33: 9 on G9294, 23 no seat) = 2; the same 2 carry "group split". Party of 24 (697F9V, all 24 without a seat) not counted and unmarked; parties of 12 and 10 likewise. API: groups_split 2, split=true only on those 2 bookings.
- G9805 21 Nov, new run 22:28Z (2daaca76…): tile/box 0; list 174 rows, 35 bookings, none with mixed outcomes; party of 48 all without a seat and party of 49 all on one flight not counted; API 0.
- EVALUATOR sees the same G9298 summary (2 / 2). Screenshots `QA-2026-11-22-04/screenshots/occ-01…occ-06`, `eval-01`.

## QA-DA-006 · "group split" marker missing on travellers without a seat
- Feature: cancellation analysis – "Passengers in priority order" list (shared passenger table) · Release: local build 2026-11-22 · Environment: local :8080, Chrome · Account: OCC.
- Preconditions: a cancellation where a booking is split between a seat and no seat (e.g. G9298 20 Nov).
- Steps: Cancellation → G9298 20 Nov → Passengers to rebook → Show all 176 → find booking 61C15M (party of 35) → compare a seated traveller (e.g. row 1) with one without a seat (e.g. row 12, open Details).
- Expected: every traveller of a booking that could not stay together is identifiable as such (the fix states the marker uses the same per-booking rule as the count).
- Actual: "group split" appears only on the 12 seated travellers (3 of 61C15M, 9 of 601TQ8); the 54 travellers of the same bookings without a seat show "No seat within 24 h" with no marker and no hint in Details, although the API flags them split=true.
- Evidence: `QA-2026-11-22-04/screenshots/occ-04-cancel-G9298-unseated-member-no-marker.jpg`, `occ-02-cancel-G9298-rebooking-box-list.jpg`.
- Reproducibility: always.
- Severity: Low (display only; count and data correct) · Priority: P4.
- Impact: an agent handling an unseated traveller cannot see from the list that part of the party was moved ahead.
- Suspected area (suspicion): `frontend/src/Shared.tsx` ~l.232 renders the marker only inside the seated branch (`p.assigned_flight_id ? … : "No seat within 24 h"`). Pre-existing rendering, unchanged by this fix.

## QA-DA-007 · Selected day chip label disappears on hover
- Feature: search launcher – "Day" filter chips (Flight Delay page; same launcher on Cancellation and the agent page) · Release: production 2026-11-22 · Environment: production http://92.5.154.198:8080, Chrome (desktop, 1568 px wide) · Account: OCC (signed in by the user).
- Preconditions: signed in; Flight Delay page.
- Steps: type "G9519" in the flight search → click day chip "Sat 21" → keep the mouse over the chip.
- Expected: the selected chip stays readable (blue background, white label) while hovered, like any other selected control.
- Actual: while hovered, the selected chip turns light grey (rgb 240,241,243) with white text (rgb 255,255,255), so "Sat 21" is invisible; it reappears when the mouse moves away.
- Evidence: `QA-2026-11-22-05/screenshots/occ-08-QA-DA-007-selected-day-chip-hover.png`; computed style of the hovered chip: class `chip-btn on`, color rgb(255,255,255), background rgb(240,241,243).
- Reproducibility: always (every selected day chip, including "All").
- Severity: Low (visual, momentary; no data impact) · Priority: P4.
- Impact: the user briefly cannot read which day is selected when pointing at it; looks broken in a demo.
- Suspected area (suspicion): `frontend/src/styles.css` – the generic `button:hover:not(:disabled)` background rule (l.186) outranks `.chip-btn.on` (l.1751) in specificity, but the white `color` of `.chip-btn.on` stays.

## Production regression QA-2026-11-22-05 (production 2026-11-22, OCC / EVALUATOR / PCU)
- Closed bugs QA-DA-001…004: behaviour confirmed on production (split count 2 = list, distinguishable Recent chips, sign-in subtitle "OCC, PCU and evaluators" in the served bundle).
- Known limitations still present: QA-DA-005 ("1 FLIGHTS MATCH "G9519"" with the Sat 21 filter), QA-DA-006 ("group split" on the 12 seated travellers of G9298 20 Nov only).
- New: QA-DA-007 (Low/P4, open).
