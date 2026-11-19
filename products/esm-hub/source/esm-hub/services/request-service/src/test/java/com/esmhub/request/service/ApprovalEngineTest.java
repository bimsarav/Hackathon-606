package com.esmhub.request.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.request.service.approval.ApprovalEngine;
import com.esmhub.request.service.approval.ApprovalEngine.StepSpec;
import com.esmhub.request.service.approval.RequestApproval;
import com.esmhub.request.service.catalogue.ApprovalStep;
import com.esmhub.common.security.CurrentUser;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ApprovalEngineTest {
    List<ApprovalStep> steps = List.of(new ApprovalStep(2, "ROLE", "SERVICE_MANAGER", new BigDecimal("1000")),
            new ApprovalStep(1, "MANAGER", null, BigDecimal.ZERO));

    static CurrentUser user(long id, String... roles) {
        return new CurrentUser(id, 1, Set.of(roles), Set.of(), "n", "e@x");
    }

    @Test
    void cheapRequestOnlyHasManagerStep() {
        assertThat(ApprovalEngine.applicableSteps(steps, new BigDecimal("999.99"))).extracting(StepSpec::order).containsExactly(1);
        assertThat(ApprovalEngine.applicableSteps(steps, null)).extracting(StepSpec::order).containsExactly(1);
    }

    @Test
    void costAtThresholdAddsRoleStepInOrder() {
        var list = ApprovalEngine.applicableSteps(steps, new BigDecimal("1000"));
        assertThat(list).extracting(StepSpec::order).containsExactly(1, 2);
        assertThat(ApprovalEngine.nextAfter(list, 1)).contains(new StepSpec(2, "ROLE", "SERVICE_MANAGER"));
        assertThat(ApprovalEngine.nextAfter(list, 2)).isEmpty();
    }

    @Test
    void managerStepResolvesToManagerOrFallsBackToRole() {
        var mgr = new StepSpec(1, "MANAGER", null);
        assertThat(ApprovalEngine.resolve(mgr, 7L).userId()).isEqualTo(7L);
        assertThat(ApprovalEngine.resolve(mgr, null).role()).isEqualTo("SERVICE_MANAGER");
        assertThat(ApprovalEngine.resolve(new StepSpec(2, "ROLE", "ASSET_MANAGER"), 7L).role()).isEqualTo("ASSET_MANAGER");
    }

    @Test
    void canDecideRules() {
        var byUser = new RequestApproval(1, 1, 7L, null, Instant.now());
        var byRole = new RequestApproval(1, 2, null, "SERVICE_MANAGER", Instant.now());
        assertThat(ApprovalEngine.canDecide(byUser, 3, user(7))).isTrue();
        assertThat(ApprovalEngine.canDecide(byUser, 3, user(8, "SERVICE_MANAGER"))).isFalse();
        assertThat(ApprovalEngine.canDecide(byRole, 3, user(8, "SERVICE_MANAGER"))).isTrue();
        assertThat(ApprovalEngine.canDecide(byRole, 3, user(8, "EMPLOYEE"))).isFalse();
        // segregation of duties: the requester can never decide, even when holding the role
        assertThat(ApprovalEngine.canDecide(byRole, 8, user(8, "SERVICE_MANAGER"))).isFalse();
        byUser.decide("APPROVED", null, 7, Instant.now());
        assertThat(ApprovalEngine.canDecide(byUser, 3, user(7))).isFalse();
    }
}
