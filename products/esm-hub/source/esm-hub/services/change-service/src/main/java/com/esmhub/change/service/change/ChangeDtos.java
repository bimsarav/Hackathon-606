package com.esmhub.change.service.change;

import com.esmhub.change.service.approval.ApprovalDtos.ApprovalView;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.List;

public final class ChangeDtos {
    private ChangeDtos() {}

    public record ChangeIn(@NotBlank @Size(max = 200) String title, @NotBlank @Size(max = 10000) String description,
                           @NotNull @Pattern(regexp = "STANDARD|NORMAL|EMERGENCY") String changeType,
                           @Pattern(regexp = "LOW|MEDIUM|HIGH") String riskLevel,
                           @Pattern(regexp = "LOW|MEDIUM|HIGH") String impact, @Positive Long ownerTeamId,
                           Instant plannedStart, Instant plannedEnd, @Size(max = 10000) String rollbackPlan) {}

    public record StatusIn(@NotNull @Pattern(regexp = "ASSESSMENT|APPROVAL|IMPLEMENTING|IMPLEMENTED|FAILED|CLOSED|CANCELLED") String status) {}

    public record ChangeView(long changeId, String changeNo, String title, String description, String changeType,
                             String status, String riskLevel, String impact, long requesterId, String requesterName,
                             Long ownerTeamId, Instant plannedStart, Instant plannedEnd, Instant actualStart,
                             Instant actualEnd, String rollbackPlan, Instant createdAt, boolean planLocked,
                             boolean assessmentComplete, List<String> missingAssessment, List<ApprovalView> approvals,
                             boolean canEdit, boolean canImplement) {}

    public record CalendarEntry(long changeId, String changeNo, String title, String changeType, String status,
                                String riskLevel, Long ownerTeamId, Instant plannedStart, Instant plannedEnd,
                                List<Long> collidesWith) {}
}
