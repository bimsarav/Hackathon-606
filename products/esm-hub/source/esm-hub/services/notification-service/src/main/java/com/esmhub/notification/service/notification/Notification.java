package com.esmhub.notification.service.notification;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "notifications")
public class Notification {
    public static final String IN_APP = "IN_APP";
    public static final String EMAIL = "EMAIL";
    public static final String PENDING = "PENDING";
    public static final String DELIVERED = "DELIVERED";
    public static final String SENT = "SENT";
    public static final String FAILED = "FAILED";
    public static final String DEAD = "DEAD";

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "notification_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "user_id") private long userId;
    private String channel;
    private String subject;
    private String body;
    private String link;
    private String reference;
    @Column(name = "entity_type") private String entityType;
    @Column(name = "entity_id") private String entityId;
    @Column(name = "delivery_status") private String deliveryStatus;
    private int attempts;
    @Column(name = "next_attempt_at") private Instant nextAttemptAt = Instant.now();
    @Column(name = "last_error") private String lastError;
    @Column(name = "event_id") private UUID eventId;
    @Column(name = "created_at") private Instant createdAt = Instant.now();
    @Column(name = "sent_at") private Instant sentAt;
    @Column(name = "read_at") private Instant readAt;

    protected Notification() {}

    public Notification(long companyId, long userId, String channel, String subject, String body, String link,
                        String reference, String entityType, String entityId, UUID eventId) {
        this.companyId = companyId; this.userId = userId; this.channel = channel;
        this.subject = subject == null ? "(no subject)" : truncate(subject, 200);
        this.body = body == null ? "" : body;
        this.link = truncate(link, 200); this.reference = truncate(reference, 60);
        this.entityType = truncate(entityType, 50); this.entityId = truncate(entityId, 60); this.eventId = eventId;
        this.deliveryStatus = IN_APP.equals(channel) ? DELIVERED : PENDING;
        if (IN_APP.equals(channel)) this.sentAt = this.createdAt;
    }

    private static String truncate(String s, int max) { return s == null || s.length() <= max ? s : s.substring(0, max); }

    /** Exponential backoff: 2^attempts minutes, capped at 60. */
    public static Duration backoff(int attempts) {
        return Duration.ofMinutes(Math.min(60L, 1L << Math.min(attempts, 10)));
    }

    public void recordSent(Instant now) {
        deliveryStatus = SENT; sentAt = now; lastError = null;
    }

    /** Records a failed send: DEAD once {@code maxAttempts} is reached, otherwise FAILED with the next retry time. */
    public void recordFailure(String error, int maxAttempts, Instant now) {
        attempts++;
        lastError = error == null ? null : truncate(error, 500);
        if (attempts >= maxAttempts) {
            deliveryStatus = DEAD;
        } else {
            deliveryStatus = FAILED;
            nextAttemptAt = now.plus(backoff(attempts));
        }
    }

    /** Admin retry: back to the queue with a fresh attempt counter. */
    public void requeue(Instant now) {
        deliveryStatus = PENDING; attempts = 0; nextAttemptAt = now; lastError = null;
    }

    public boolean isRetryable() { return EMAIL.equals(channel) && (DEAD.equals(deliveryStatus) || FAILED.equals(deliveryStatus)); }

    public void markRead(Instant now) { if (readAt == null) readAt = now; }

    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public long getUserId() { return userId; }
    public String getChannel() { return channel; }
    public String getSubject() { return subject; }
    public String getBody() { return body; }
    public String getLink() { return link; }
    public String getReference() { return reference; }
    public String getEntityType() { return entityType; }
    public String getEntityId() { return entityId; }
    public String getDeliveryStatus() { return deliveryStatus; }
    public int getAttempts() { return attempts; }
    public Instant getNextAttemptAt() { return nextAttemptAt; }
    public String getLastError() { return lastError; }
    public UUID getEventId() { return eventId; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getSentAt() { return sentAt; }
    public Instant getReadAt() { return readAt; }
}
