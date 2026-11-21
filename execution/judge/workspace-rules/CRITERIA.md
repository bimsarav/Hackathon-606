# Judge criteria – workspace rules (area code WR)

Applies to changes of the workspace rules (`instructions/`, `CLAUDE.md`, hooks, tracking conventions) made at the user's request. Derived from the requests that produced them (2026-11-21 AI Judge, 2026-11-22 Manual QA) and from the integration requirements those requests contain (MASTER_PROMPT §16.11, §17.14).

| # | Category | Weight | What is assessed |
|---|---|---:|---|
| 1 | Fidelity | 15 | User text saved verbatim where required; the raw request stored in `input/instructions/`; conventions kept apart from the verbatim text |
| 2 | Integration | 20 | Hooks in every affected part of the master prompt (roles, phases, quality rules, reporting, commands, definition of done, other roles) and in the summary rule files |
| 3 | Preservation / no conflict | 15 | Nothing existing removed or weakened; no contradictions with other sections or rule files |
| 4 | User additions fulfilled | 25 | The specific things the user asked for in their own words are met and traceable |
| 5 | Proportionality | 10 | Routine work is not over-burdened; depth matches risk |
| 6 | Independence | 5 | Assurance roles run separately from the producing agent |
| 7 | Workspace consistency and safety | 5 | Resume, logs, archive, memory, safety rules |
| 8 | Product artefacts | 5 | Effect on product deliverables (no traces, correct locations) |

Mandatory: no existing rule weakened; no conflict with the safety rules. Critical: a change that would let the agent bypass user approval, handle secrets unsafely, or put internal process material into client deliverables.

| Date | Change |
|---|---|
| 2026-11-22 | Created (finding J-WR-017), from the categories of EVAL-2026-11-21-01 and EVAL-2026-11-22-01. |
