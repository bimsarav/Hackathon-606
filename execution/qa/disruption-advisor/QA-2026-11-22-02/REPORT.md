# QA report QA-2026-11-22-02 · disruption-advisor · local · retest of fixes + previously blocked cases

(Content returned by the QA agent, whose own write to this file was refused; saved by the coordinating session.)

## A. Overview and limitations
Scope: QA-DA-001 (PDF rebuilt); evaluator cases blocked in cycle 1 (TC-30); OCC/PCU sign-in with the login file (TC-31). App regression for the PDF rebuild skipped per brief. QA-DA-002/003 out of scope. Release: local build of 2026-11-22 (uncommitted tree, v1.0.0). Environment: localhost:8080, Chrome, desktop width only. Limitations: L1 Test data upload/edit/save/remove not run (brief rule). L2 no crew roster locally. L3 API role checks used tokens from the login endpoint (supplementary). Records created: delay G9519 +150, cancellation G9805, 1 reward plan (not approved). No approvals, uploads or edits.

## B. Execution summary
23 cases · 22 executed · 21 passed · 1 failed · 0 blocked · 1 not tested · 95.5 %.

## C. Coverage
QA-DA-001 verified fixed. Evaluator: sign-in, menu, Model Card hub + 9 details, Test data read-only, Watchlist panel + risk/model 200, delay with reward note and hotel labels, cancellation, Recent Searches, API 200 — all PASS. OCC/PCU: sign-in, menu, API 403 — PASS. Sign-out PASS. Sign-in wording FAIL (QA-DA-004).

## D. Defects
C0 H0 M0 L1 (P4 1): QA-DA-004 sign-in subtitle omits the evaluator role. Closed: QA-DA-001. Still open (out of scope): QA-DA-002 (L/P3), QA-DA-003 (L/P4).

## E. Risks
Test data write paths untested in the UI; crew "within limits" state unverifiable locally; release uncommitted; QA-DA-002/003 awaiting decision.

## F. Verdict
QA PASSED WITH OBSERVATIONS.
