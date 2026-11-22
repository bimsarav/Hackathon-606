# QA report QA-2026-11-22-05 · disruption-advisor · production regression

**A. Overview & limitations:** production http://92.5.154.198:8080, release 2026-11-22, Chrome desktop only. Roles OCC/EVALUATOR/PCU signed in by the user. The sign-in subtitle was checked in the served code, not on screen. No approvals, uploads, edits or new agent runs. 2 option selections (POST /select) were made on G9519 during OCC before the read-only rule; the selection ends on the recommended option (A6-ARI). Console capture started after each role's first page load.

**B. Execution:** 36 cases, 36 executed, 35 passed, 1 failed, 0 blocked / not tested, **97.2%** (OCC 22/23, EVALUATOR 7/7, PCU 6/6).

**C. Coverage:** the brief's regression suite for each role. Fixes QA-DA-001…004 and J-DA-009–013, 015, 016 behave correctly on production.

**D. Defects:** C0 H0 M0 L1. QA-DA-007 (Low/P4, Open): a selected Day chip's label disappears on hover. Known limitations (user: do not fix) still present: QA-DA-005, QA-DA-006.

**E. Risks:** "Select" saves a selection that every viewer sees; raw IDs in the agent step text (e.g. "protect_passengers"); approval and upload paths not exercised on production.

**F. Verdict:** QA PASSED WITH OBSERVATIONS.

QA: QA PASSED WITH OBSERVATIONS · 35/36 passed (97.2%) · bugs C0 H0 M0 L1 · report: execution/qa/disruption-advisor/QA-2026-11-22-05/REPORT.md
