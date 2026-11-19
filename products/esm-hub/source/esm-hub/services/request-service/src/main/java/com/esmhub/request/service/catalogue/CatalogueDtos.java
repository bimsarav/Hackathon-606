package com.esmhub.request.service.catalogue;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.util.List;

public final class CatalogueDtos {
    private CatalogueDtos() {}

    public record StepIO(@Min(1) @Max(10) int stepOrder, @NotNull @Pattern(regexp = "MANAGER|ROLE") String approverType,
                         @Size(max = 60) String approverRole, @DecimalMin("0") BigDecimal minCost) {}

    public record ItemIn(@Positive long serviceId, @NotBlank @Size(min = 3, max = 150) String name,
                         @Size(max = 5000) String description, @DecimalMin("0") BigDecimal baseCost,
                         Long fulfilmentTeamId, Boolean active, @Valid List<StepIO> steps) {}

    public record ItemView(long itemId, long serviceId, String serviceName, String name, String description,
                           BigDecimal baseCost, Long fulfilmentTeamId, boolean active, List<StepIO> steps) {}
}
