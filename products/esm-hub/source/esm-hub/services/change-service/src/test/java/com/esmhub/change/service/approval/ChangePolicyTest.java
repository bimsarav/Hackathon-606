package com.esmhub.change.service.approval;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.change.service.approval.ChangePolicy.Step;
import com.esmhub.common.security.CurrentUser;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ChangePolicyTest {
    static CurrentUser user(long id, String... roles) { return new CurrentUser(id, 1, Set.of(roles), Set.of(), "u", "u@x"); }

    @Test void standardIsPreApproved() { assertThat(ChangePolicy.steps("STANDARD", "HIGH")).isEmpty(); }

    @Test void emergencyNeedsOnlyChangeManager() {
        assertThat(ChangePolicy.steps("EMERGENCY", "HIGH")).containsExactly(new Step(1, "CHANGE_MANAGER"));
    }

    @Test void normalLowOrMediumNeedsChangeManager() {
        assertThat(ChangePolicy.steps("NORMAL", "LOW")).containsExactly(new Step(1, "CHANGE_MANAGER"));
        assertThat(ChangePolicy.steps("NORMAL", "MEDIUM")).containsExactly(new Step(1, "CHANGE_MANAGER"));
    }

    @Test void normalHighAddsServiceManagerSecond() {
        assertThat(ChangePolicy.steps("NORMAL", "HIGH")).containsExactly(new Step(1, "CHANGE_MANAGER"), new Step(2, "SERVICE_MANAGER"));
    }

    @Test void roleHolderCanDecideButNotTheRequester() {
        ChangeApproval a = new ChangeApproval(1, 1, "CHANGE_MANAGER", Instant.now());
        assertThat(ChangePolicy.canDecide(a, 9, user(2, "CHANGE_MANAGER"))).isTrue();
        assertThat(ChangePolicy.canDecide(a, 2, user(2, "CHANGE_MANAGER"))).isFalse();   // segregation of duties
        assertThat(ChangePolicy.canDecide(a, 9, user(3, "SERVICE_MANAGER"))).isFalse();
        assertThat(ChangePolicy.canDecide(a, 9, user(4, "ADMIN"))).isFalse();
    }

    @Test void decidedApprovalCannotBeDecidedAgain() {
        ChangeApproval a = new ChangeApproval(1, 1, "CHANGE_MANAGER", Instant.now());
        a.decide("APPROVED", null, 2, Instant.now());
        assertThat(ChangePolicy.canDecide(a, 9, user(2, "CHANGE_MANAGER"))).isFalse();
        assertThat(List.of(a.getApproverId())).containsExactly(2L);
    }
}
