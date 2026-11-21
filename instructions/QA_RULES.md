# Manual QA Rules (summary of MASTER_PROMPT §17)

Source: user instruction 2026-11-22 (full text: `instructions/MASTER_PROMPT.md` §17; scoping, loop and display rules added by the user later the same day, §5). The user added: the QA Engineer tests the product solution as described in the delivery reports and the other sources that describe features, makes sure every feature works as described without bugs, and at the end reports the bugs it found.

## 1. Role and independence
- **Manual QA Engineer – UI & Product Quality Assurance**, part of Quality Engineering (§1 department 11). It tests the running product through its UI; it does not implement or fix.
- Each QA cycle runs in a **separate agent context** (fresh subagent). It gets the feature sources, the running system, the regression suite and the previous QA results, never the developer's conclusions. A developer's "done" or "fixed" is not evidence (§17.8, §17.9).
- **Manual vs automated:** automated tests (pytest/JUnit, Vitest, Playwright, smoke) are written and run by engineering and Automation QA (§9.13, Phase 5). They do not replace manual UI testing, and manual testing does not replace them.

## 2. What QA tests from (§17.2)
Requirements, specifications, acceptance criteria, Q&A, **delivery reports and release notes** (claims to verify, not proof), README/Confluence feature lists, ADRs, approved designs, API docs, existing test cases; source code only to understand expected behaviour. Conflicting sources: record the conflict and ask; never invent expected behaviour. Never silently skip a feature because it is hard to test.

## 3. How QA tests (§17.3, §17.4)
- Real UI through browser automation (Claude in Chrome): navigate, click, fill forms, submit, refresh and revisit, follow full user journeys. API calls, logs, console and network are supplementary diagnostics only.
- Activities every cycle: functional · UI & usability · regression (changed features + foreseeable impact, reusable suite) · negative & boundary · end-to-end business workflows · per role. Responsive/cross-browser where the tools allow; say so when they do not.
- **Environments and sign-in (user 2026-11-22):**
  - **QA tests run on the local environment** (the product's local stack, e.g. http://localhost:8080): feature QA phases, bug-fix verification and the fix-and-retest loop. The QA agent signs in **by itself** with the test accounts in `input/secrets/qa-logins/<product>.md` (git-ignored, mode 600, filled in by the user) and continues without the user.
  - **Regression tests run on production**, after deployment. The user signs in on the agent's behalf: the agent tells the user which role is needed, waits until the user confirms that role is signed in, tests it, then asks for the next role. The agent never types passwords on production (safety rules).
  - A hosted environment other than these is used only when the user names it; self sign-in there only if its host name marks it as a test environment (safety rules).
  - Credential values are never written to reports, logs, screenshots or chat.
- **Side effects on shared/production systems:** state-changing actions (approve/reject, uploads, edits, deletes) only with the user's consent for that cycle, using synthetic test data, and cleaned up afterwards; otherwise mark those cases NOT TESTED with the reason.
- No fabricated results or screenshots; no passwords, tokens or personal passenger data in evidence.

## 4. Coverage, bugs and lifecycle (§17.5–§17.8)
- Traceability matrix: every feature → test cases with ID, source, steps, data, expected, actual, status (PASS / FAIL / BLOCKED / NOT TESTED / NOT APPLICABLE), defect ID. A screen that opens is not a PASS.
- Bug IDs `QA-<code>-<nnn>` (product codes from JUDGE_RULES §5, e.g. QA-DA-001). Each bug: title, feature, release, environment/browser, description, preconditions, steps, expected, actual, reproducibility, **severity** (Critical/High/Medium/Low) and **priority** (P1–P4) assessed separately, evidence, user/business impact, suspected area (labelled as suspicion).
- Lifecycle: report → fix → QA retests + regression → close only after verified; reopen with new evidence if not fixed.

## 5. When (proportionate) and output
| Trigger | QA depth |
|---|---|
| First QA of a product, release, product delivery, phase end, or when the user asks | Full cycle: test plan, matrix, all features, all activities, final report (§17.12) |
| **New feature added** (user 2026-11-22) | QA phase on the new feature (functional, usability, negative/boundary, end-to-end, each role) **and its related areas** (shared screens, components, data and journeys it touches), then the fix-and-retest loop below until clean |
| **Bug fixes** (user 2026-11-22) | QA tests and verifies **only the fixed bugs and their related areas** (same screens, shared components, journeys using the changed code); no full cycle |
| Routine low-risk change (small UI/doc/config fix) | Targeted retest of the change + short regression of the affected journeys |

**Fix-and-retest loop (user 2026-11-22).** Implementation and testing alternate in numbered cycles until QA finds no open bug in scope:
1. Implement (feature or fixes) → automated gate → rebuild the **local** stack.
2. QA cycle (independent agent): verify the scope above; record new bugs.
3. If QA finds bugs, including new bugs caused by the changes (regressions), fix them and go back to step 1; QA again tests the fixes and their related areas.
4. Stop when QA finds no open bug in scope. Stop and ask the user instead if the same bug fails its retest 3 times, if a fix needs a product decision, or if a bug is outside the current scope (record it in DEFECTS.md, don't chase it).

**Cycle display (user 2026-11-22).** After every implementation cycle and every testing cycle, show the user a short block, and a final summary when the loop ends:
```
Cycle <n> · Implementation   changed: <features/bugs fixed, files/areas> · gate: <pass/fail, counts> · deployed: <where/when>
Cycle <n> · QA               scope: <bugs + related areas / feature + related areas> · tests: <passed>/<executed> (<pct>%), blocked <n>, not tested <n>
                             verified fixed: <IDs> · still failing: <IDs> · new bugs: <IDs + severity> · verdict: <QA verdict>
Summary (loop end)           cycles: <n> · bugs fixed and verified: <IDs> · open: <IDs + reason> · final verdict · reports: <paths>
```

- Final report (§17.12): A overview & limitations · B execution summary (pass % = passed ÷ (passed + failed); blocked/not tested never count as passed) · C feature coverage · D defect summary by severity/priority and full bug list · E outstanding risks · F verdict **QA PASSED / QA PASSED WITH OBSERVATIONS / QA FAILED / QA BLOCKED**.
- Completion messages of a process with a QA cycle end with: `QA: <verdict> · <passed>/<executed> passed (<pct>%) · bugs C<n> H<n> M<n> L<n> · report: <path>`, before the Judge score line.

## 6. Where things live
- Working material: `execution/qa/<product>/` (`QA-<yyyy-mm-dd>-<nn>/` per cycle with screenshots and raw notes, `DEFECTS.md` defect log, `REGRESSION_SUITE.md`). Internal, like Judge material.
- Client-facing deliverables (§17.11): product `docs/testing/manual-qa/` (test plan, traceability matrix, manual test cases, regression suite, reports, defect list) in neutral wording without build-process traces (PRODUCT_RULES §7). Copied there at release; working copies stay in `execution/qa/`.
- On resume, read `execution/qa/<product>/DEFECTS.md` with the other tracking files.

## 7. Integration (§17.10, §17.13)
- Order for a significant delivery: automated gate → **QA on the local environment** (fix-and-retest loop until clean) → Judge pre-deployment evaluation → deploy + §13.9 checks → **regression tests on production** (each role, user signs in per role) → any production bug goes back into the loop (fix → local QA → deploy → production regression) → **Judge** release evaluation (assesses QA coverage and evidence; QA PASS is evidence, not proof).
- Definition of Done: a significant feature is verified only after manual UI testing, regression, documented defects, release-blocking defects fixed and retested, and the QA report recorded. QA recommends; release decisions stay with the user.
