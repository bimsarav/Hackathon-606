package com.esmhub.request.service.catalogue;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import java.math.BigDecimal;

/** One approval step of a catalogue item. Applies only when the request cost reaches {@code minCost}. */
@Embeddable
public class ApprovalStep {
    @Column(name = "step_order") private int stepOrder;
    @Column(name = "approver_type") private String approverType;
    @Column(name = "approver_role") private String approverRole;
    @Column(name = "min_cost") private BigDecimal minCost = BigDecimal.ZERO;

    protected ApprovalStep() {}

    public ApprovalStep(int stepOrder, String approverType, String approverRole, BigDecimal minCost) {
        this.stepOrder = stepOrder;
        this.approverType = approverType;
        this.approverRole = approverRole;
        this.minCost = minCost == null ? BigDecimal.ZERO : minCost;
    }

    public int getStepOrder() { return stepOrder; }
    public String getApproverType() { return approverType; }
    public String getApproverRole() { return approverRole; }
    public BigDecimal getMinCost() { return minCost; }
}
