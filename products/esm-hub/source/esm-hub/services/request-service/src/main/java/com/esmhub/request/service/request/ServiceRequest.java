package com.esmhub.request.service.request;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "service_requests")
public class ServiceRequest {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "request_id") private Long id;
    @Column(name = "request_no") private String requestNo;
    @Column(name = "company_id") private long companyId;
    @Column(name = "requester_id") private long requesterId;
    @Column(name = "service_id") private Long serviceId;
    @Column(name = "item_id") private Long itemId;
    private String title;
    private String details;
    private String status;
    @Column(name = "estimated_cost") private BigDecimal estimatedCost;
    @Column(name = "assigned_team_id") private Long assignedTeamId;
    @Column(name = "assigned_user_id") private Long assignedUserId;
    @Column(name = "requested_at") private Instant requestedAt;
    @Column(name = "updated_at") private Instant updatedAt;
    @Column(name = "approved_at") private Instant approvedAt;
    @Column(name = "fulfilled_at") private Instant fulfilledAt;

    protected ServiceRequest() {}

    public ServiceRequest(long companyId, long requesterId, Long serviceId, Long itemId, String title, String details,
                          BigDecimal estimatedCost, Long assignedTeamId, Instant now) {
        this.requestNo = "TMP-" + java.util.UUID.randomUUID().toString().substring(0, 15);
        this.companyId = companyId; this.requesterId = requesterId; this.serviceId = serviceId; this.itemId = itemId;
        this.title = title; this.details = details; this.estimatedCost = estimatedCost; this.assignedTeamId = assignedTeamId;
        this.status = "SUBMITTED"; this.requestedAt = now; this.updatedAt = now;
    }

    public void assignNumber() { this.requestNo = String.format("REQ-%06d", id); }

    public void setStatus(String status, Instant now) {
        this.status = status;
        this.updatedAt = now;
        if ("APPROVED".equals(status)) approvedAt = now;
        if ("FULFILLED".equals(status)) fulfilledAt = now;
    }

    public void assignTo(Long userId) { this.assignedUserId = userId; }

    public Long getId() { return id; }
    public String getRequestNo() { return requestNo; }
    public long getCompanyId() { return companyId; }
    public long getRequesterId() { return requesterId; }
    public Long getServiceId() { return serviceId; }
    public Long getItemId() { return itemId; }
    public String getTitle() { return title; }
    public String getDetails() { return details; }
    public String getStatus() { return status; }
    public BigDecimal getEstimatedCost() { return estimatedCost; }
    public Long getAssignedTeamId() { return assignedTeamId; }
    public Long getAssignedUserId() { return assignedUserId; }
    public Instant getRequestedAt() { return requestedAt; }
    public Instant getApprovedAt() { return approvedAt; }
    public Instant getFulfilledAt() { return fulfilledAt; }
}
