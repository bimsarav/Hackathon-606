# Demo seed tooling

The supplied ESMP dump (`legacy/esmp_sample_dump.sql`, synthetic data) is converted into one Flyway migration per
service (`db/seed/V900__demo_seed.sql`), which is applied only with the `demo` Spring profile.

1. `tools/seed/legacy-db.sh up` starts PostgreSQL with the repaired dump loaded (`repair_dump.py` fixes the 3 syntax defects).
2. `tools/seed/queries/<service>.sql` holds SELECT statements that **emit SQL text** for the service's own tables, e.g.
   `SELECT format('INSERT INTO users (id, email) VALUES (%s, %L);', user_id, email) FROM esmp.users ORDER BY 1;`
   It ends by advancing identity sequences, e.g. `SELECT 'SELECT setval(pg_get_serial_sequence(''users'',''id''), (SELECT max(id) FROM users));';`
3. `tools/seed/export.sh <service>` writes the migration. Commit the generated file.

Rules: keep legacy IDs (other services reference them); repair the data issues listed in `docs/data/data-quality-report.md`
where the target schema requires it (and say so in a comment); never invent data that contradicts the dump.
