# Architecture Rules
- Microservices split by business domain (bounded contexts), each owning its data. No service reads another service's database.
- One entry point: Spring Cloud Gateway (routing, auth token relay, rate limiting, CORS).
- Synchronous REST for queries and commands that need an immediate answer; Kafka events for state changes other services react to (notifications, audit, reporting projections, integrations).
- Reliability: transactional outbox → Kafka; consumers idempotent (dedupe by event ID); retries with backoff and dead-letter topics; Resilience4j circuit breakers on synchronous calls.
- Cross-cutting: correlation ID propagated through HTTP headers and Kafka headers; structured JSON logs; Actuator health/readiness; Micrometer metrics.
- Every significant choice is an ADR in the product repo's `docs/architecture/adr/`.
