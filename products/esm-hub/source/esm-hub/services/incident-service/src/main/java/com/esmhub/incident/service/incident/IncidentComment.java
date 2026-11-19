package com.esmhub.incident.service.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "incident_comments")
public class IncidentComment {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "comment_id") private Long id;
    @Column(name = "incident_id") private long incidentId;
    @Column(name = "author_id") private long authorId;
    private String body;
    @Column(name = "is_internal") private boolean internal;
    @Column(name = "created_at") private Instant createdAt;

    protected IncidentComment() {}

    public IncidentComment(long incidentId, long authorId, String body, boolean internal, Instant createdAt) {
        this.incidentId = incidentId;
        this.authorId = authorId;
        this.body = body;
        this.internal = internal;
        this.createdAt = createdAt;
    }

    public Long getId() { return id; }
    public long getIncidentId() { return incidentId; }
    public long getAuthorId() { return authorId; }
    public String getBody() { return body; }
    public boolean isInternal() { return internal; }
    public Instant getCreatedAt() { return createdAt; }
}
