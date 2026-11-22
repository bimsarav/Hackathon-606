# QA report QA-2026-11-22-01 · disruption-advisor · local · bug-fix verification

(Content returned by the QA agent, whose own write to this file was refused by the harness; saved unchanged in substance by the coordinating session.)

## A. Overview and limitations
Scope: bug-fix verification of J-DA-011/012/015/016 + re-check of J-DA-004/009/010/013 + regression of the shared screens. Release: local build of 2026-11-22 (uncommitted tree on v1.0.0). Environment: localhost:8080, Chrome 1920×933 (no responsive/cross-browser).
Limitations: L1 the QA login file's local rows did not match the local stack (401); OCC and PCU were tested with the stack's own local test accounts. L2 no evaluator account on the local stack → evaluator cases BLOCKED. L3 no crew roster locally → J-DA-004 only in the "no data" state. L4 the scenario dropdown is never rendered → renamed option checked in code only (N/A). L5 no new agent run.
Records created locally: delay G9519 +150 and cancellation G9298 (OCC), delay G9502 +150 (PCU), 2 reward plans (not approved), 1 AI draft. No approvals, rejections, uploads or edits.

## B. Execution summary
33 cases · 29 executed · 26 passed · 3 failed · 2 blocked · 1 not tested · 1 N/A · pass rate 89.7 %.

## C. Coverage
J-DA-011 VERIFIED FIXED · J-DA-012 VERIFIED FIXED (reward vs booked note, hotel labels, Recent Searches) · J-DA-015 PARTLY FIXED (PDF not rebuilt → QA-DA-001) · J-DA-016 VERIFIED FIXED ("21 Nov 17:45 UTC", AI and template) · J-DA-004 verified in "no data" state · J-DA-009/010/013 VERIFIED FIXED. Regression PASS: navigation (OCC, PCU), Flight Delay, Watchlist, agent console (existing run), Recent Searches, role limits (UI + API 403), wrong-credential sign-in, sign-out. FAIL: cancellation split count (QA-DA-002), launcher Recent chips (QA-DA-003). BLOCKED: evaluator. NOT TESTED: new agent run.

## D. Defects
C0 H0 M0 L3 (P2 1, P3 1, P4 1): QA-DA-001 solution-design PDF still shows the developer branch name (Low/P2) · QA-DA-002 cancellation "Protected 12 · 90 booking(s) split" (Low/P3, pre-existing) · QA-DA-003 launcher Recent chips not distinguishable (Low/P4, pre-existing). Details and evidence: DEFECTS.md, TRACEABILITY.md, screenshots/.

## E. Risks
Evaluator role untested; crew "within limits" wording unverified locally; release uncommitted (J-DA-017); new agent run not exercised.

## F. Verdict
QA FAILED (low severity). Rebuild the PDF and retest; retest evaluator cases once an evaluator account exists; QA-DA-002/003 pre-existing: fix in this loop or defer by decision.
