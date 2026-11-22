# QA report QA-2026-11-22-03 · disruption-advisor · local · bug-fix verification (QA-DA-002/003/004)

(Content returned by the QA agent, whose own write to this file was refused; saved by the coordinating session.)

## A. Overview and limitations
Scope: QA-DA-002/003/004 + related areas (Cancellation tiles/boxes/rewards note/hotel label, Flight Delay rebooking box, Recent Searches, launcher search/day chips/suggestions) for OCC; EVALUATOR and PCU pass (sign-in, cancellation summary, Recent chips). Release: local build 2026-11-22 (uncommitted, v1.0.0). localhost:8080, Chrome, desktop width only. Limits: no approvals/rejections/uploads/edits; API reads used only to check chip de-duplication and split data; scenarios saved before the fix keep their old number (accepted). Records created: cancellation G9298 20 Nov, 1 reward plan on G9805 (not approved).
## B. Execution summary
20 cases · 20 executed · 18 passed · 2 failed · 0 blocked · 0 not tested · 90.0 %.
## C. Coverage
QA-DA-004 verified fixed. QA-DA-003 verified fixed (labels, newest-run de-duplication, tooltip, reopen on both pages, 3 roles). QA-DA-002 partly fixed: number is bookings and wording is clear, but a booking that stayed together (party of 24, all without a seat) is counted: G9298 shows 3, the list marks 2. Regression PASS on all related areas. New: QA-DA-005. Observation (not a bug): Recent Searches says "Your last 20 scenarios" but lists other users' runs too (pre-existing).
## D. Defects
C0 H0 M0 L2 (P3 1, P4 1): QA-DA-002 reopened (Low/P3) · QA-DA-005 "1 FLIGHTS MATCH" plural (Low/P4, pre-existing). Closed: QA-DA-003, QA-DA-004.
## E. Risks
The split count overstated bookings when a large group got no seat at all; old saved scenarios show a traveller count under the new booking label; release uncommitted.
## F. Verdict
QA FAILED (low severity). Fix QA-DA-002 to count bookings whose travellers ended on different outcomes; retest.
