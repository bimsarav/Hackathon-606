package com.esmhub.incident.service.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** Timeline entry of an incident. */
@Entity
@Table(name = "incident_events")
public class IncidentEvent {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "event_id") private Long id;
    @Column(name = "incident_id") private long incidentId;
    @Column(name = "event_type") private String eventType;
    @Column(name = "from_value") private String fromValue;
    @Column(name = "to_value") private String toValue;
    @Column(name = "actor_id") private Long actorId;
    @Column(name = "occurred_at") private Instant occurredAt;

    protected IncidentEvent() {}

    public IncidentEvent(long incidentId, String eventType, Long actorId, Object from, Object to, Instant occurredAt) {
        this.incidentId = incidentId;
        this.eventType = eventType;
        this.actorId = actorId;
        this.fromValue = cut(from);
        this.toValue = cut(to);
        this.occurredAt = occurredAt;
    }

    private static String cut(Object v) {
        if (v == null) return null;
        String s = String.valueOf(v);
        return s.length() > 100 ? s.substring(0, 100) : s;
    }

    public Long getId() { return id; }
    public long getIncidentId() { return incidentId; }
    public String getEventType() { return eventType; }
    public String getFromValue() { return fromValue; }
    public String getToValue() { return toValue; }
    public Long getActorId() { return actorId; }
    public Instant getOccurredAt() { return occurredAt; }
}
