package com.esmhub.common.events;

import java.time.Instant;
import java.util.UUID;
import tools.jackson.databind.JsonNode;

/**
 * Standard Kafka message body (see docs/architecture/architecture.md §3).
 * State topics use eventType "&lt;aggregate&gt;.snapshot" with the full current state as payload.
 */
public record EventEnvelope(UUID eventId, String eventType, Instant occurredAt, Long companyId, Long actorId,
                            String correlationId, String aggregateType, String aggregateId, int version, JsonNode payload) {
}
