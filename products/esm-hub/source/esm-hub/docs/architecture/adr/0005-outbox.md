# ADR-0005: Transactional outbox, idempotent consumers, dead-letter topics

- **Status:** Accepted (2026-11-19)
- **Context:** Notifications, audit and replicas must never miss or duplicate effects of committed changes (FR-11, FR-12, NFR-11).
- **Decision:** Events are written to outbox_events in the business transaction and relayed in order by OutboxRelay (SKIP LOCKED). Consumers record processed event IDs. Failures retry with backoff, then go to a <topic>.DLT topic.
- **Consequences:** At-least-once delivery with exactly-once effects. Small latency (relay polling, 500 ms).
