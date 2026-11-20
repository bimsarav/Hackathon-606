package com.esmhub.change.service.approval;

import com.esmhub.common.security.CurrentUser;
import java.util.ArrayList;
import java.util.List;

/**
 * Pure change approval policy: STANDARD changes are pre-approved; every other change needs the CHANGE_MANAGER; a NORMAL
 * change with HIGH risk additionally needs the SERVICE_MANAGER (sequential, second). The requester never approves their own change.
 */
public final class ChangePolicy {
    private ChangePolicy() {}

    public record Step(int order, String role) {}

    public static List<Step> steps(String changeType, String riskLevel) {
        List<Step> steps = new ArrayList<>();
        if ("STANDARD".equals(changeType)) return steps;
        steps.add(new Step(1, "CHANGE_MANAGER"));
        if ("NORMAL".equals(changeType) && "HIGH".equals(riskLevel)) steps.add(new Step(2, "SERVICE_MANAGER"));
        return steps;
    }

    public static boolean canDecide(ChangeApproval a, long requesterId, CurrentUser me) {
        if (!a.isPending() || requesterId == me.userId()) return false;
        if (a.getApproverId() != null) return a.getApproverId() == me.userId();
        return a.getApproverRole() != null && me.roles().contains(a.getApproverRole());
    }
}
