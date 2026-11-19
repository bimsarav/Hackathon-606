# ADR-0007: CQRS reporting read model

- **Status:** Accepted (2026-11-19)
- **Context:** FR-13 dashboards aggregate across incidents, requests, changes, problems and assets owned by different services.
- **Decision:** reporting-service consumes the state topics into its own projection tables and computes reports in SQL.
- **Consequences:** Cross-domain reports without coupling. Data is eventually consistent and rebuildable from the compacted topics.
