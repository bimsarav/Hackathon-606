package com.esmhub.common.contracts;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

/**
 * Payloads of the state topics (compacted, consumed by reporting-service) and the domain-event topics (consumed by
 * notification-service). See docs/architecture/event-contracts.md. Producers own these shapes; change them only
 * additively (new nullable fields).
 */
public final class DomainContracts {
    private DomainContracts() {}

    /**
     * Carried by every domain event on *.events topics. The producer decides who is notified (it has the context);
     * notification-service creates an in-app notification and an email for each recipient.
     */
    public record NotificationIntent(List<Long> notifyUserIds, String subject, String message, String link,
                                     boolean email) {}

    /** Domain event payload: event-specific facts plus the notification intent. */
    public record DomainEvent(String entityType, String entityId, String reference, NotificationIntent notification,
                              java.util.Map<String, Object> facts) {}

    // ---------- state snapshots (event type "<aggregate>.snapshot") ----------
    public record IncidentSnapshot(long incidentId, long companyId, String ticketNo, String title, String status,
                                   boolean closed, String priority, Long serviceId, String channel, long requesterId,
                                   Long assignedTeamId, Long assignedUserId, Instant createdAt, Instant firstResponseAt,
                                   Instant resolvedAt, Instant closedAt, Instant responseDueAt, Instant dueAt,
                                   boolean responseBreached, boolean resolutionBreached, boolean slaPaused,
                                   int reopenedCount, Integer satisfactionScore, int worklogMinutes) {}

    public record ProblemSnapshot(long problemId, long companyId, String problemNo, String title, String status,
                                  boolean knownError, Long ownerTeamId, Instant createdAt, Instant resolvedAt,
                                  List<Long> incidentIds) {}

    public record RequestSnapshot(long requestId, long companyId, String requestNo, String title, String status,
                                  long requesterId, Long serviceId, Long itemId, BigDecimal estimatedCost,
                                  Long assignedTeamId, Instant requestedAt, Instant approvedAt, Instant fulfilledAt) {}

    public record ChangeSnapshot(long changeId, long companyId, String changeNo, String title, String changeType,
                                 String status, String riskLevel, String impact, Long ownerTeamId, Long requesterId,
                                 Instant plannedStart, Instant plannedEnd, Instant actualStart, Instant actualEnd,
                                 Instant createdAt) {}

    public record AssetSnapshot(long assetId, long companyId, String assetTag, String assetType, String status,
                                Long assignedUserId, Long officeId, LocalDate purchaseDate, LocalDate warrantyEnd,
                                BigDecimal purchaseCost) {}
}
