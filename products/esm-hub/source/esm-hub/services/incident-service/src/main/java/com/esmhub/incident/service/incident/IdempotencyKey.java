package com.esmhub.incident.service.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.time.Instant;

/** NFR-11: remembers the resource created for (user, Idempotency-Key, endpoint). */
@Entity
@Table(name = "idempotency_keys")
public class IdempotencyKey {
    @Embeddable
    public record Key(@Column(name = "user_id") Long userId, @Column(name = "idem_key") String idemKey,
                      @Column(name = "endpoint") String endpoint) implements Serializable {}

    @EmbeddedId private Key id;
    @Column(name = "resource_id") private long resourceId;
    @Column(name = "created_at") private Instant createdAt;

    protected IdempotencyKey() {}

    public IdempotencyKey(Key id, long resourceId, Instant createdAt) {
        this.id = id;
        this.resourceId = resourceId;
        this.createdAt = createdAt;
    }

    public long getResourceId() { return resourceId; }
}
