# ADR-0005: Parquet + DuckDB for the airline extracts; PostgreSQL only for user records

- **Status:** Accepted (2026-11-20)
- **Context:** The extracts are large: 27.9M booking rows in nested zips (Latin-1, some malformed lines) plus Excel and CSV files. They are read-mostly and analytical. engineering standards §9.25 (user rule) requires tabular data to be converted to Parquet first. The product owner said booking/inventory mismatches must not break the process.
- **Decision:**
  - A one-shot `ingest` service converts every extract to typed Parquet (zstd; bookings partitioned by departure year, sorted by departure time), counts and skips malformed rows, and builds the operating window as Parquet (`app/ingest`).
  - The API loads the window tables into in-memory DuckDB and queries them with column selection and filter push-down.
  - PostgreSQL 18 holds only scenarios, decisions and audit.
- **Consequences:**
  - Analyses answer in under a second; ingest takes 4–15 minutes once, and is skipped when the inputs are unchanged.
  - The API mounts the Parquet volume read-only.
  - Two stores to operate; the ops data is reproducible from the extracts, so only PostgreSQL needs backups.
