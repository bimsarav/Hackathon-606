# Manual QA working area (MASTER_PROMPT §17, instructions/QA_RULES.md)

Internal material of the Manual QA Engineer. Never part of a client deliverable; the client-facing QA documents are copied, in neutral wording, to the product's `docs/testing/manual-qa/` at release.

Per product `execution/qa/<product>/`:
- `REGRESSION_SUITE.md` reusable regression cases for the important business workflows (kept up to date with each release).
- `DEFECTS.md` defect log: one row per bug `QA-<code>-<nnn>` with title, severity, priority, status (open / fixed – awaiting retest / closed / reopened), found in, retested in.
- `QA-<yyyy-mm-dd>-<nn>/` one folder per testing cycle: `BRIEF.md` (exact brief given to the QA agent), `TEST_PLAN.md`, `TRACEABILITY.md` (features → test cases → status → defect), `REPORT.md` (§17.12 A–F) and `screenshots/`.
