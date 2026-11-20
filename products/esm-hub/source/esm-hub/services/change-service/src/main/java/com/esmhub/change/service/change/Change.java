package com.esmhub.change.service.change;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "changes")
public class Change {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "change_id") private Long id;
    @Column(name = "change_no") private String changeNo;
    @Column(name = "company_id") private long companyId;
    private String title;
    private String description;
    @Column(name = "change_type") private String changeType;
    private String status;
    @Column(name = "risk_level") private String riskLevel;
    private String impact;
    @Column(name = "requester_id") private long requesterId;
    @Column(name = "owner_team_id") private Long ownerTeamId;
    @Column(name = "planned_start") private Instant plannedStart;
    @Column(name = "planned_end") private Instant plannedEnd;
    @Column(name = "actual_start") private Instant actualStart;
    @Column(name = "actual_end") private Instant actualEnd;
    @Column(name = "rollback_plan") private String rollbackPlan;
    @Column(name = "created_at") private Instant createdAt;
    @Column(name = "updated_at") private Instant updatedAt;

    protected Change() {}

    public Change(long companyId, long requesterId, Instant now) {
        this.changeNo = "TMP-" + java.util.UUID.randomUUID().toString().substring(0, 15);
        this.companyId = companyId; this.requesterId = requesterId; this.status = "DRAFT";
        this.createdAt = now; this.updatedAt = now;
    }

    public void assignNumber() { this.changeNo = String.format("CHG-%06d", id); }

    /** Replaces the plan/assessment fields (only allowed while the plan is unlocked; enforced by the service). */
    public void applyPlan(String title, String description, String changeType, String riskLevel, String impact,
                          Long ownerTeamId, Instant plannedStart, Instant plannedEnd, String rollbackPlan, Instant now) {
        this.title = title; this.description = description; this.changeType = changeType; this.riskLevel = riskLevel;
        this.impact = impact; this.ownerTeamId = ownerTeamId; this.plannedStart = plannedStart;
        this.plannedEnd = plannedEnd; this.rollbackPlan = rollbackPlan; this.updatedAt = now;
    }

    public void setStatus(String status, Instant now) {
        this.status = status;
        this.updatedAt = now;
        if ("IMPLEMENTING".equals(status)) actualStart = now;
        if ("IMPLEMENTED".equals(status) || "FAILED".equals(status)) actualEnd = now;
    }

    public Long getId() { return id; }
    public String getChangeNo() { return changeNo; }
    public long getCompanyId() { return companyId; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public String getChangeType() { return changeType; }
    public String getStatus() { return status; }
    public String getRiskLevel() { return riskLevel; }
    public String getImpact() { return impact; }
    public long getRequesterId() { return requesterId; }
    public Long getOwnerTeamId() { return ownerTeamId; }
    public Instant getPlannedStart() { return plannedStart; }
    public Instant getPlannedEnd() { return plannedEnd; }
    public Instant getActualStart() { return actualStart; }
    public Instant getActualEnd() { return actualEnd; }
    public String getRollbackPlan() { return rollbackPlan; }
    public Instant getCreatedAt() { return createdAt; }
}
