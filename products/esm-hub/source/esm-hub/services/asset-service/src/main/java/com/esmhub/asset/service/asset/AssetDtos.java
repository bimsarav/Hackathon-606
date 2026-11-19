package com.esmhub.asset.service.asset;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

/** API records of the asset resource. */
public final class AssetDtos {
    private AssetDtos() {}

    public record HistoryEntry(long userId, String userName, Instant assignedAt, Instant returnedAt, Long assignedBy) {}

    /** {@code history} is null in list responses and filled by the detail endpoint. */
    public record AssetView(long assetId, String assetTag, String assetType, String manufacturer, String model,
                            String serialNumber, LocalDate purchaseDate, LocalDate warrantyEnd, Long officeId,
                            BigDecimal purchaseCost, String status, Long assignedUserId, String assignedUserName,
                            String warrantyState, Instant createdAt, List<HistoryEntry> history) {}

    public record CreateAsset(@NotBlank @Size(min = 2, max = 30) String assetTag, @NotBlank @Size(min = 2, max = 40) String assetType,
                              @Size(max = 60) String manufacturer, @Size(max = 80) String model, @Size(max = 80) String serialNumber,
                              LocalDate purchaseDate, LocalDate warrantyEnd, Long officeId,
                              @DecimalMin("0") BigDecimal purchaseCost) {}

    public record UpdateAsset(@Size(max = 60) String manufacturer, @Size(max = 80) String model, LocalDate warrantyEnd,
                              Long officeId, @DecimalMin("0") BigDecimal purchaseCost) {}

    public record AssignAsset(@NotNull Long userId) {}

    public record ChangeStatus(@NotNull @Pattern(regexp = "IN_STOCK|ASSIGNED|REPAIR|RETIRED|LOST") String status) {}
}
