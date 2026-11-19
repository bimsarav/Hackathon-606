# ADR-0008: Legacy dump becomes per-service demo seed migrations

- **Status:** Accepted (2026-11-19)
- **Context:** The supplied dump is single-schema, has 3 syntax defects and serves as demo data.
- **Decision:** tools/seed repairs the dump, loads it in a throwaway PostgreSQL and generates db/seed/V900__demo_seed.sql per service (legacy IDs preserved), applied only with the demo profile.
- **Consequences:** Production never contains synthetic data. The legacy data-quality issues stay visible, as documented.
