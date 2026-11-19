# ADR-0003: Company is the tenant boundary

- **Status:** Accepted (2026-11-19) · pending PO review
- **Context:** PS §7 asks whether offices are legal entities (BQ-7). The data is single-company but multi-office.
- **Decision:** company_id on every business row; every query filters on the caller's cid claim; foreign records return 404. Offices are locations (timezone, calendar).
- **Consequences:** Safe multi-company growth. Reference config such as priorities and calendars is shared unless scoped later.
