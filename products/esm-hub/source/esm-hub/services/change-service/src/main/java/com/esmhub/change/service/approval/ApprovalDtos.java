package com.esmhub.change.service.approval;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;

public final class ApprovalDtos {
    private ApprovalDtos() {}

    public record DecisionIn(@NotNull @Pattern(regexp = "APPROVED|REJECTED") String decision, @Size(max = 2000) String comments) {}

    public record ApprovalView(long approvalId, long changeId, String reference, String title, String changeType,
                               String riskLevel, int stepOrder, Long approverId, String approverRole, String decision,
                               String comments, Instant createdAt, Instant decidedAt) {}
}
