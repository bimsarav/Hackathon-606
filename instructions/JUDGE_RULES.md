# AI Judge Rules (summary of MASTER_PROMPT §16)

Source: user instruction 2026-11-21 (full text: `instructions/MASTER_PROMPT.md` §16). The user added: criteria change per product and follow its requirements and specification; a score is given at every process completion.

## 1. Role and independence
- The **AI Judge – Engineering Quality, Architecture & Delivery Evaluator** is an independent assurance function, not an implementation team. It evaluates the deliverables of every department; it does not replace the reviews owned by Architecture, QA, Security or DevOps.
- The producing agent never approves its own deliverable. Evaluations run in a **separate agent context** (a fresh subagent). It receives the deliverable paths, the product criteria, the evidence (test logs, deployment logs, the running system) and the previous evaluation, never the producer's conclusions or summary of "what was done well".
- The Judge distinguishes verified findings, inferred risks and recommendations, and never claims a test passed or a feature works without evidence it inspected itself.
- The Judge recommends. It never changes code, standards, the master prompt or requirements on its own, and never relaxes requirements to make work pass. Final decisions stay with the user.

## 2. Criteria per product
- Each product has `execution/judge/<product>/CRITERIA.md`, written before its first evaluation. It is derived from the product's own requirements and specification: client judging weights, acceptance criteria, submission rules and mandatory constraints.
- Where the specification gives weights, use them as the score categories and use the §16.4 categories as the assessment lens inside each. Where it gives none, use the §16.4 defaults (Business 10, Architecture 15, Code 15, Security 10, Performance/Reliability 10, Testing 15, DevOps 10, Documentation 5, Maintainability 5, Business value 5).
- Mandatory acceptance rules and critical-failure rules are listed in the criteria file. A critical failure blocks approval whatever the score (§16.4, §16.6).
- When requirements or the specification change, update the criteria and record the change and its date in the file.

## 3. When to evaluate (proportionate, §16.10)
| Process completion | Depth | Output |
|---|---|---|
| Routine low-risk change (docs, small fix, config) | Short scorecard: re-score only the affected categories, carry the others from the last full evaluation and mark them "carried" | Score line in the completion message + entry in the tracker |
| Significant deliverable (feature, design, data/model change, deck, Confluence set) | Scorecard for the affected categories + findings | Report `EVAL-<date>-<nn>.md` |
| Phase end, deployment (before and after), release, product delivery, and the delivery-cadence gates (design diagrams shown to the user, MVP hosted, approval of each later phase) | Full §16.5 report (A–F) on the whole product | Report `EVAL-<date>-<nn>.md` |
| Lifecycle checkpoints (MASTER_PROMPT §4): requirements validation (end of Phase 1), architecture and design review (before the Technology Selection Gate), implementation review (each increment), deployment and production readiness (Phase 6, §13.13, §14.8) | As in the rows above, by size | As above |

Do not create approval bottlenecks for routine work: the short scorecard never blocks unless it finds a critical issue.
The **first** evaluation of a product is always a full one; carried scores are only allowed once a full evaluation exists. Several small changes completed together get one short scorecard, not one each.

## 4. Score at process completion
Every completion message for a process that produced or changed a deliverable ends with:
`Judge score: <nn>/100 (<classification>) · verdict <APPROVED | APPROVED WITH IMPROVEMENTS | REWORK REQUIRED | REJECTED> · critical findings: <n> · report: execution/judge/<product>/EVAL-…md`
Scale: 90–100 Excellent · 80–89 Very Good · 70–79 Good · 60–69 Needs Improvement · <60 Unsatisfactory. The score never hides a critical finding; list critical findings separately.

## 5. Reports, history and tracking
- Reports: `execution/judge/<product>/EVAL-<yyyy-mm-dd>-<nn>.md` with §16.5 sections A–F. Findings have IDs `J-<product-code>-<nnn>`, severity (Critical/High/Medium/Low), impact, recommended action, expected outcome, responsible role, and acceptance criteria for closing them.
- Re-evaluations keep the original findings and record status changes (open → resolved → verified) and the score difference to the previous evaluation.
- `execution/judge/QUALITY_TRACKER.md`: one row per evaluation (date, product, scope, score, verdict, critical/high count) plus a list of recurring weaknesses. When a weakness recurs, recommend a change to the standards or agent rules, and ask the user before changing them (§16.7).
- **Briefs are kept:** the exact brief given to the Judge is saved as `BRIEF-<yyyy-mm-dd>-<nn>.md` next to its report, so the evidence and wording given to the Judge can be checked for bias later.
- **Accepted risks:** only the user can accept the risk of an open critical finding; record the date, finding ID and the user's words in the report. The finding stays listed as an accepted risk.
- **Non-product deliverables** (workspace rules, research, tooling) get their own folder and criteria: `execution/judge/<area>/CRITERIA.md`, derived from the request that produced them.
- **Finding IDs:** `J-<code>-<nnn>`; codes: DA = disruption-advisor, ESM = esm-hub, WR = workspace rules, KB = airline knowledge base. Add a code here when a new product or area starts.
- **Resume and archive:** on resume, read `execution/judge/QUALITY_TRACKER.md` with the other tracking files; at product delivery, the product's `execution/judge/<product>/` folder is archived with its logs.
- **Manual QA (MASTER_PROMPT §17.10):** in every product evaluation, assess the latest QA cycle in `execution/qa/<product>/` (coverage of the delivery-report features, evidence quality, open defects by severity). A QA PASS is evidence to check, not proof; a significant delivery without a UI-based QA cycle is a finding.
- Judge material is internal: never put it in `products/<product>/` or on the client's Confluence (PRODUCT_RULES §7).
