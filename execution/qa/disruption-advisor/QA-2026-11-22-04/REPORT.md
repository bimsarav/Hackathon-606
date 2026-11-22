# QA report QA-2026-11-22-04 · disruption-advisor · local · retest of reopened QA-DA-002

## A. Overview and limitations
Scope: QA-DA-002 (reopened in cycle 3) on new analyses G9298 20 Nov and G9805 21 Nov; related areas: cancellation tiles and the three boxes, passenger-list markers, Flight Delay rebooking box (G9519 21 Nov +120), Recent chips on both pages; OCC, plus an EVALUATOR check of the G9298 summary. Out of scope: QA-DA-005. Release: local build 2026-11-22 (uncommitted, v1.0.0); API container recreated 02:26 +04 with the fix. localhost:8080, Chrome, desktop width. Limits: analyses only (no approvals/rejections/uploads/edits); API reads used only as a supplementary check. Records created: 3 analyses (listed in TRACEABILITY.md).

## B. Execution summary
13 cases · 13 executed · 12 passed · 1 failed · 0 blocked · 0 not tested · 92.3 %.

## C. Coverage
QA-DA-002 verified fixed: G9298 tile and box show 2; the passenger list has exactly 2 bookings with travellers on different outcomes (party of 35: 3 seated / 31 without; party of 33: 9 / 23), the same 2 carry "group split"; the party of 24 that stayed together without seats (and parties of 12 and 10) are not counted. G9805 21 Nov: 0 shown, 0 in the list, a party of 48 all without seats not counted; API agrees for both. Regression PASS: cancellation tiles/boxes consistent, Flight Delay rebooking box (27 / 2 / 27 hotel rooms), Recent chips (newest runs, reopen correctly), EVALUATOR summary identical, sign-out.
New: QA-DA-006 – the "group split" marker appears only on travellers who got a seat; travellers of the same split booking without a seat show no marker.

## D. Defects
C0 H0 M0 L1 new (P4 1): QA-DA-006 (Low/P4, display gap in the passenger list; pre-existing rendering, data correct). Closed this cycle: QA-DA-002. Still open, out of scope: QA-DA-005 (Low/P4).

## E. Risks
An agent looking at an unseated traveller of a split booking cannot see from the list that part of the party was moved; the summary count is now correct. Scenarios saved before the fix keep their stored number. Release uncommitted.

## F. Verdict
QA PASSED WITH OBSERVATIONS. QA-DA-002 closed; one new low-severity display bug (QA-DA-006), not release-blocking; QA-DA-005 awaits the user's decision.
