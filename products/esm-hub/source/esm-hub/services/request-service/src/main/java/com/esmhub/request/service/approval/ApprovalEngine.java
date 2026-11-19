package com.esmhub.request.service.approval;

import com.esmhub.request.service.catalogue.ApprovalStep;
import com.esmhub.common.security.CurrentUser;
import java.math.BigDecimal;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

/**
 * Pure rules of the sequential approval engine (BQ-5): steps run in order, a step applies only when the cost reaches
 * its min_cost, a MANAGER step goes to the requester's line manager (fallback: SERVICE_MANAGER role), and the
 * requester can never approve their own request.
 */
public final class ApprovalEngine {
    public static final String FALLBACK_ROLE = "SERVICE_MANAGER";

    private ApprovalEngine() {}

    public record StepSpec(int order, String type, String role) {}

    public record Approver(Long userId, String role) {}

    public static List<StepSpec> applicableSteps(List<ApprovalStep> steps, BigDecimal cost) {
        BigDecimal c = cost == null ? BigDecimal.ZERO : cost;
        return steps.stream().sorted(Comparator.comparingInt(ApprovalStep::getStepOrder))
                .filter(s -> c.compareTo(s.getMinCost()) >= 0)
                .map(s -> new StepSpec(s.getStepOrder(), s.getApproverType(), s.getApproverRole())).toList();
    }

    public static Optional<StepSpec> nextAfter(List<StepSpec> steps, int afterOrder) {
        return steps.stream().filter(s -> s.order() > afterOrder).min(Comparator.comparingInt(StepSpec::order));
    }

    /** managerId is the requester's line manager from the directory replica, or null. */
    public static Approver resolve(StepSpec step, Long managerId) {
        if ("MANAGER".equals(step.type())) {
            return managerId != null ? new Approver(managerId, null) : new Approver(null, FALLBACK_ROLE);
        }
        return new Approver(null, step.role());
    }

    public static boolean canDecide(RequestApproval a, long requesterId, CurrentUser me) {
        if (!a.isPending() || requesterId == me.userId()) return false;
        if (a.getApproverId() != null) return a.getApproverId() == me.userId();
        return a.getApproverRole() != null && me.roles().contains(a.getApproverRole());
    }
}
