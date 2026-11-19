# Next Action
- **Action:** Sort every file in `input/inbox/` (except README.md) into the right `input/` subfolder: requirements, problem-domain, data, solution-documents, reference-material or existing-code. Record each move in the execution log. Ask the user whether the data is sensitive and should go in .gitignore. Then run the full Phase 1 analysis.
- **Files:** `input/inbox/*`, `input/**`, `execution/BLOCKERS.md`
- **Prerequisites:** The user has placed material in `input/inbox/`.
- **Expected outcome:** An empty inbox; `documentation/business/requirements-analysis.md`; populated `instructions/*_RULES.md`; a list of follow-up questions.
- **Validation:** Every requirement traces back to a supplied document or a user answer.
- **Risks:** Inventing requirements. Committing sensitive data.
