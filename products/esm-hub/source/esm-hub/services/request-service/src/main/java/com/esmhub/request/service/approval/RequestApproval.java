package com.esmhub.request.service.approval;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "request_approvals")
public class RequestApproval {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "approval_id") private Long id;
    @Column(name = "request_id") private long requestId;
    @Column(name = "step_order") private int stepOrder;
    @Column(name = "approver_id") private Long approverId;
    @Column(name = "approver_role") private String approverRole;
    private String decision;
    private String comments;
    @Column(name = "created_at") private Instant createdAt;
    @Column(name = "decided_at") private Instant decidedAt;
    @Column(name = "decided_by") private Long decidedBy;

    protected RequestApproval() {}

    public RequestApproval(long requestId, int stepOrder, Long approverId, String approverRole, Instant now) {
        this.requestId = requestId; this.stepOrder = stepOrder; this.approverId = approverId;
        this.approverRole = approverRole; this.decision = "PENDING"; this.createdAt = now;
    }

    public void decide(String decision, String comments, long by, Instant now) {
        this.decision = decision; this.comments = comments; this.decidedBy = by; this.decidedAt = now;
        if (approverId == null) approverId = by;
    }

    public boolean isPending() { return "PENDING".equals(decision); }
    public Long getId() { return id; }
    public long getRequestId() { return requestId; }
    public int getStepOrder() { return stepOrder; }
    public Long getApproverId() { return approverId; }
    public String getApproverRole() { return approverRole; }
    public String getDecision() { return decision; }
    public String getComments() { return comments; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getDecidedAt() { return decidedAt; }
}
