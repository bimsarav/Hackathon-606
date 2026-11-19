package com.esmhub.notification.service.notification;

import java.time.Instant;

public final class NotificationDtos {
    private NotificationDtos() {}

    public record NotificationView(long id, String channel, String subject, String body, String link, String reference,
                                   String entityType, String entityId, String deliveryStatus, Instant createdAt,
                                   Instant sentAt, Instant readAt) {
        static NotificationView of(Notification n) {
            return new NotificationView(n.getId(), n.getChannel(), n.getSubject(), n.getBody(), n.getLink(),
                    n.getReference(), n.getEntityType(), n.getEntityId(), n.getDeliveryStatus(), n.getCreatedAt(),
                    n.getSentAt(), n.getReadAt());
        }
    }

    public record AdminNotificationView(long id, long userId, String recipient, String channel, String subject,
                                        String deliveryStatus, int attempts, Instant nextAttemptAt, String lastError,
                                        Instant createdAt, Instant sentAt) {}

    public record UnreadCount(long unread) {}
}
