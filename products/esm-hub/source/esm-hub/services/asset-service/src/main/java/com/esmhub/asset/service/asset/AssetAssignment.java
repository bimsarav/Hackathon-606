package com.esmhub.asset.service.asset;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "asset_assignments")
public class AssetAssignment {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "assignment_id") private Long id;
    @Column(name = "asset_id") private long assetId;
    @Column(name = "user_id") private long userId;
    @Column(name = "assigned_at") private Instant assignedAt;
    @Column(name = "returned_at") private Instant returnedAt;
    @Column(name = "assigned_by") private Long assignedBy;

    protected AssetAssignment() {}

    public AssetAssignment(long assetId, long userId, Instant assignedAt, Long assignedBy) {
        this.assetId = assetId; this.userId = userId; this.assignedAt = assignedAt; this.assignedBy = assignedBy;
    }

    public void close(Instant at) { this.returnedAt = at.isBefore(assignedAt) ? assignedAt : at; }

    public Long getId() { return id; }
    public long getAssetId() { return assetId; }
    public long getUserId() { return userId; }
    public Instant getAssignedAt() { return assignedAt; }
    public Instant getReturnedAt() { return returnedAt; }
    public Long getAssignedBy() { return assignedBy; }
}
