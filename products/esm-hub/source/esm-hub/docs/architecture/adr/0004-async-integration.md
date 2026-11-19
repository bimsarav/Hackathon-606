# ADR-0004: Asynchronous integration through Kafka state topics

- **Status:** Accepted (2026-11-19)
- **Context:** Services need each other's data (users, teams, services, office timezones), and synchronous calls would couple their availability.
- **Decision:** Owners publish compacted state topics. Consumers keep local read replicas (esm-directory-replica, reporting projections). There are no synchronous service-to-service calls.
- **Consequences:** High availability and loose coupling. Replicas are eventually consistent, typically within seconds.
