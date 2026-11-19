package com.esmhub.request.service.request;

import com.esmhub.request.service.approval.ApprovalDtos.ApprovalView;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public final class RequestDtos {
    private RequestDtos() {}

    public record CreateRequest(@Positive long itemId, @Size(max = 200) String title, @Size(max = 10000) String details,
                                @DecimalMin("0") BigDecimal estimatedCost) {}

    public record StatusIn(@NotNull @Pattern(regexp = "IN_PROGRESS|FULFILLED|CANCELLED") String status) {}

    public record RequestView(long requestId, String requestNo, String title, String details, String status,
                              long requesterId, String requesterName, Long serviceId, Long itemId,
                              BigDecimal estimatedCost, Long assignedTeamId, Long assignedUserId, Instant requestedAt,
                              Instant approvedAt, Instant fulfilledAt, List<ApprovalView> approvals, boolean canFulfil) {}
}
