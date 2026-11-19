package com.esmhub.common.events;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/** A message waiting to be relayed to Kafka. Written in the business transaction (transactional outbox). */
@Entity
@Table(name = "outbox_events")
public class OutboxEvent {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "event_id", nullable = false, unique = true)
    private UUID eventId;
    @Column(nullable = false)
    private String topic;
    @Column(name = "message_key", nullable = false)
    private String messageKey;
    @Column(name = "event_type", nullable = false)
    private String eventType;
    /** JSON envelope, or null for a tombstone. */
    private String payload;
    @Column(name = "correlation_id")
    private String correlationId;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
    @Column(name = "published_at")
    private Instant publishedAt;
    private int attempts;
    @Column(name = "last_error")
    private String lastError;

    protected OutboxEvent() {}

    public OutboxEvent(UUID eventId, String topic, String messageKey, String eventType, String payload, String correlationId) {
        this.eventId = eventId;
        this.topic = topic;
        this.messageKey = messageKey;
        this.eventType = eventType;
        this.payload = payload;
        this.correlationId = correlationId;
        this.createdAt = Instant.now();
    }

    public Long getId() { return id; }
    public UUID getEventId() { return eventId; }
    public String getTopic() { return topic; }
    public String getMessageKey() { return messageKey; }
    public String getEventType() { return eventType; }
    public String getPayload() { return payload; }
    public String getCorrelationId() { return correlationId; }
    public Instant getPublishedAt() { return publishedAt; }
    public int getAttempts() { return attempts; }
    public String getLastError() { return lastError; }

    void markPublished() { this.publishedAt = Instant.now(); this.lastError = null; }
    void markFailed(String error) { this.attempts++; this.lastError = error == null ? null : error.substring(0, Math.min(500, error.length())); }
}
