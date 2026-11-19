# ESMP Sample Project Pack

## Files
- `esmp_sample_dump.sql`: PostgreSQL schema and synthetic seed data.
- `PROBLEM_STATEMENT.md`: business problem, scope, requirements and expected deliverables.
- `DATA_DICTIONARY.md`: table descriptions and suggested analysis questions.

## Load the database
Requires PostgreSQL 15+.

```bash
createdb esmp_dev
psql -d esmp_dev -f esmp_sample_dump.sql
```

The dump creates schema `esmp`. Tables are inside that schema.

## Important
All names, emails, tickets, assets, events and IP addresses are synthetic. Email addresses use `example.test`; IP addresses use the documentation-only `192.0.2.0/24` range. The dataset is designed for architecture, SQL, analytics, API, workflow, testing and security exercises. It is not production data.

## Suggested first instruction to Claude
Read the master prompt and all files in `input/`. Analyse the problem statement and database dump first. Do not start coding. Produce a domain analysis, data-quality report, ERD, requirements backlog, architecture options and a list of clarification questions. Record findings in the execution files.
