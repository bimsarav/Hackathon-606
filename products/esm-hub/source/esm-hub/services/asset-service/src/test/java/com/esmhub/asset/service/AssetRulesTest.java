package com.esmhub.asset.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.asset.service.asset.AssetRules;
import java.time.LocalDate;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class AssetRulesTest {
    static final LocalDate TODAY = LocalDate.of(2026, 6, 1);

    @ParameterizedTest
    @CsvSource({"IN_STOCK,REPAIR,true", "IN_STOCK,ASSIGNED,true", "ASSIGNED,IN_STOCK,true", "ASSIGNED,RETIRED,false",
            "REPAIR,RETIRED,true", "REPAIR,LOST,false", "LOST,IN_STOCK,true", "LOST,REPAIR,false", "RETIRED,IN_STOCK,false"})
    void assetFlow(String from, String to, boolean allowed) {
        assertThat(AssetRules.canMove(from, to)).isEqualTo(allowed);
    }

    @Test
    void onlyStockedOrAssignedAssetsCanBeAssigned() {
        assertThat(AssetRules.canAssignFrom("IN_STOCK")).isTrue();
        assertThat(AssetRules.canAssignFrom("ASSIGNED")).isTrue();
        assertThat(AssetRules.canAssignFrom("REPAIR")).isFalse();
        assertThat(AssetRules.canAssignFrom("RETIRED")).isFalse();
    }

    @Test
    void warrantyStates() {
        assertThat(AssetRules.warrantyState(null, TODAY)).isEqualTo("UNKNOWN");
        assertThat(AssetRules.warrantyState(TODAY.minusDays(1), TODAY)).isEqualTo("EXPIRED");
        assertThat(AssetRules.warrantyState(TODAY, TODAY)).isEqualTo("EXPIRING");
        assertThat(AssetRules.warrantyState(TODAY.plusDays(90), TODAY)).isEqualTo("EXPIRING");
        assertThat(AssetRules.warrantyState(TODAY.plusDays(91), TODAY)).isEqualTo("ACTIVE");
    }
}
