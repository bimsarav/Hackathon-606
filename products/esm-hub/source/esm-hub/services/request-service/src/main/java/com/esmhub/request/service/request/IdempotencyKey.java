package com.esmhub.request.service.request;

import jakarta.persistence.*;
import java.io.Serializable;
import java.time.Instant;

@Entity
@Table(name = "idempotency_keys")
@IdClass(IdempotencyKey.Pk.class)
public class IdempotencyKey {
    public record Pk(long userId, String key, String scope) implements Serializable {}

    @Id @Column(name = "user_id") private long userId;
    @Id @Column(name = "idem_key") private String key;
    @Id private String scope;
    @Column(name = "entity_id") private long entityId;
    @Column(name = "created_at") private Instant createdAt = Instant.now();

    protected IdempotencyKey() {}
    public IdempotencyKey(long userId, String key, String scope, long entityId) {
        this.userId = userId; this.key = key; this.scope = scope; this.entityId = entityId;
    }
    public long getEntityId() { return entityId; }
}
