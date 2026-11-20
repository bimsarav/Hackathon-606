package com.esmhub.audit.service.audit;

import java.time.Instant;
import tools.jackson.databind.JsonNode;

public final class AuditDtos {
    private AuditDtos() {}

    public record AuditView(long auditId, String service, Long actorUserId, String entityType, String entityId, String action,
                            JsonNode oldValues, JsonNode newValues, String sourceIp, String correlationId, Instant occurredAt) {}

    /** All filters optional; times are inclusive instants. */
    public record AuditFilter(String service, String entityType, String entityId, String action, Long actorId,
                              Instant from, Instant to) {}
}
