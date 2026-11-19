package com.esmhub.asset.service.asset;

import java.time.LocalDate;
import java.util.Map;
import java.util.Set;

/** Pure business rules of the asset lifecycle (FR-9). */
public final class AssetRules {
    private AssetRules() {}

    public static final String IN_STOCK = "IN_STOCK", ASSIGNED = "ASSIGNED", REPAIR = "REPAIR", RETIRED = "RETIRED", LOST = "LOST";
    public static final int EXPIRING_DAYS = 90;

    /** Allowed status moves. ASSIGNED is entered only through the assign operation. */
    public static final Map<String, Set<String>> FLOW = Map.of(
            IN_STOCK, Set.of(ASSIGNED, REPAIR, RETIRED, LOST),
            ASSIGNED, Set.of(IN_STOCK, REPAIR, LOST),
            REPAIR, Set.of(IN_STOCK, RETIRED),
            LOST, Set.of(IN_STOCK, RETIRED),
            RETIRED, Set.of());

    public static boolean canMove(String from, String to) {
        return FLOW.getOrDefault(from, Set.of()).contains(to);
    }

    public static boolean canAssignFrom(String status) {
        return IN_STOCK.equals(status) || ASSIGNED.equals(status);
    }

    /** ACTIVE, EXPIRING (within 90 days), EXPIRED or UNKNOWN (no warranty date). */
    public static String warrantyState(LocalDate warrantyEnd, LocalDate today) {
        if (warrantyEnd == null) return "UNKNOWN";
        if (warrantyEnd.isBefore(today)) return "EXPIRED";
        return warrantyEnd.isAfter(today.plusDays(EXPIRING_DAYS)) ? "ACTIVE" : "EXPIRING";
    }
}
