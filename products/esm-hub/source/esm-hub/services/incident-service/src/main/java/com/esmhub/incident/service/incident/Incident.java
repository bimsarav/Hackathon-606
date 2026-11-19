package com.esmhub.incident.service.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PostLoad;
import jakarta.persistence.PostPersist;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.data.domain.Persistable;

/** Incident aggregate (FR-3, FR-5). The id is drawn from the identity sequence first so the ticket number can use it. */
@Entity
@Table(name = "incidents")
public class Incident implements Persistable<Long> {
    @Id @Column(name = "incident_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "ticket_no") private String ticketNo;
    private String title;
    private String description;
    @Column(name = "requester_id") private long requesterId;
    @Column(name = "service_id") private Long serviceId;
    @Column(name = "asset_id") private Long assetId;
    @Column(name = "priority_id") private int priorityId;
    @Column(name = "status_id") private int statusId;
    @Column(name = "assigned_team_id") private Long assignedTeamId;
    @Column(name = "assigned_user_id") private Long assignedUserId;
    @Column(name = "sla_id") private Long slaId;
    private String channel;
    @Column(name = "created_at") private Instant createdAt;
    @Column(name = "updated_at") private Instant updatedAt;
    @Column(name = "first_response_at") private Instant firstResponseAt;
    @Column(name = "resolved_at") private Instant resolvedAt;
    @Column(name = "closed_at") private Instant closedAt;
    @Column(name = "response_due_at") private Instant responseDueAt;
    @Column(name = "due_at") private Instant dueAt;
    @Column(name = "sla_paused_since") private Instant slaPausedSince;
    @Column(name = "sla_paused_minutes") private int slaPausedMinutes;
    @Column(name = "response_breached") private boolean responseBreached;
    @Column(name = "resolution_breached") private boolean resolutionBreached;
    @Column(name = "resolution_code") private String resolutionCode;
    @Column(name = "resolution_notes") private String resolutionNotes;
    @Column(name = "satisfaction_score") private Integer satisfactionScore;
    @Column(name = "reopened_count") private int reopenedCount;
    @Transient private boolean isNew;

    protected Incident() {}

    public Incident(long id, long companyId, String title, String description, long requesterId, Long serviceId,
                    Long assetId, int priorityId, int statusId, Long assignedTeamId, String channel, Instant now) {
        this.id = id;
        this.companyId = companyId;
        this.ticketNo = String.format("INC-%06d", id);
        this.title = title;
        this.description = description;
        this.requesterId = requesterId;
        this.serviceId = serviceId;
        this.assetId = assetId;
        this.priorityId = priorityId;
        this.statusId = statusId;
        this.assignedTeamId = assignedTeamId;
        this.channel = channel;
        this.createdAt = now;
        this.updatedAt = now;
        this.isNew = true;
    }

    @Override public Long getId() { return id; }
    @Override public boolean isNew() { return isNew; }
    @PostLoad @PostPersist void markNotNew() { isNew = false; }

    /** Fields recorded in audit events (no free text). */
    public Map<String, Object> auditState() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("title", title);
        m.put("serviceId", serviceId);
        m.put("assetId", assetId);
        m.put("priorityId", priorityId);
        m.put("statusId", statusId);
        m.put("assignedTeamId", assignedTeamId);
        m.put("assignedUserId", assignedUserId);
        m.put("requesterId", requesterId);
        m.put("slaId", slaId);
        m.put("dueAt", dueAt == null ? null : dueAt.toString());
        m.put("resolutionCode", resolutionCode);
        m.put("reopenedCount", reopenedCount);
        m.put("satisfactionScore", satisfactionScore);
        return m;
    }

    public long getCompanyId() { return companyId; }
    public String getTicketNo() { return ticketNo; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getDescription() { return description; }
    public long getRequesterId() { return requesterId; }
    public void setRequesterId(long requesterId) { this.requesterId = requesterId; }
    public Long getServiceId() { return serviceId; }
    public void setServiceId(Long serviceId) { this.serviceId = serviceId; }
    public Long getAssetId() { return assetId; }
    public void setAssetId(Long assetId) { this.assetId = assetId; }
    public int getPriorityId() { return priorityId; }
    public void setPriorityId(int priorityId) { this.priorityId = priorityId; }
    public int getStatusId() { return statusId; }
    public void setStatusId(int statusId) { this.statusId = statusId; }
    public Long getAssignedTeamId() { return assignedTeamId; }
    public Long getAssignedUserId() { return assignedUserId; }
    public void assignTo(Long teamId, Long userId) { this.assignedTeamId = teamId; this.assignedUserId = userId; }
    public Long getSlaId() { return slaId; }
    public void setSlaId(Long slaId) { this.slaId = slaId; }
    public String getChannel() { return channel; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void touch(Instant now) { this.updatedAt = now; }
    public Instant getFirstResponseAt() { return firstResponseAt; }
    public void setFirstResponseAt(Instant t) { this.firstResponseAt = t; }
    public Instant getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(Instant t) { this.resolvedAt = t; }
    public Instant getClosedAt() { return closedAt; }
    public void setClosedAt(Instant t) { this.closedAt = t; }
    public Instant getResponseDueAt() { return responseDueAt; }
    public Instant getDueAt() { return dueAt; }
    public void setDueDates(Instant responseDue, Instant due) { this.responseDueAt = responseDue; this.dueAt = due; }
    public Instant getSlaPausedSince() { return slaPausedSince; }
    public void setSlaPausedSince(Instant t) { this.slaPausedSince = t; }
    public int getSlaPausedMinutes() { return slaPausedMinutes; }
    public void addPausedMinutes(int m) { this.slaPausedMinutes += m; }
    public boolean isResponseBreached() { return responseBreached; }
    public void setResponseBreached(boolean b) { this.responseBreached = b; }
    public boolean isResolutionBreached() { return resolutionBreached; }
    public void setResolutionBreached(boolean b) { this.resolutionBreached = b; }
    public String getResolutionCode() { return resolutionCode; }
    public String getResolutionNotes() { return resolutionNotes; }
    public void setResolution(String code, String notes) { this.resolutionCode = code; this.resolutionNotes = notes; }
    public Integer getSatisfactionScore() { return satisfactionScore; }
    public void setSatisfactionScore(Integer s) { this.satisfactionScore = s; }
    public int getReopenedCount() { return reopenedCount; }
    public void incrementReopened() { this.reopenedCount++; }
}
