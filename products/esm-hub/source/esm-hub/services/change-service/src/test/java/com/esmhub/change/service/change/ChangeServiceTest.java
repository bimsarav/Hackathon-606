package com.esmhub.change.service.change;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.change.service.approval.ApprovalService;
import com.esmhub.change.service.approval.ChangePolicy;
import com.esmhub.change.service.change.ChangeDtos.ChangeIn;
import com.esmhub.change.service.events.ChangeEvents;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.directory.DirectoryLookup;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class ChangeServiceTest {
    ChangeRepository repo = mock(ChangeRepository.class);
    ApprovalService approvals = mock(ApprovalService.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    ChangeEvents events = mock(ChangeEvents.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    ChangeService service;
    Instant start = Instant.now().plus(2, ChronoUnit.DAYS);

    CurrentUser cm = new CurrentUser(2, 1, Set.of("CHANGE_MANAGER"), Set.of(), "cm", "cm@x");
    CurrentUser tech = new CurrentUser(5, 1, Set.of("TECHNICIAN"), Set.of(1L), "tech", "t@x");
    CurrentUser employee = new CurrentUser(7, 1, Set.of("EMPLOYEE"), Set.of(), "e", "e@x");

    @BeforeEach
    void setUp() {
        service = new ChangeService(repo, approvals, directory, events, audit);
        when(directory.teamLead(any())).thenReturn(Set.of());
        when(directory.isMember(any(), anyLong())).thenReturn(false);
        when(directory.name(anyLong())).thenReturn("n");
        when(approvals.chain(anyLong())).thenReturn(List.of());
        when(approvals.involves(anyLong(), any())).thenReturn(false);
    }

    Change change(String type, String status, boolean complete) {
        Change c = new Change(1, 5, Instant.now());
        ReflectionTestUtils.setField(c, "id", 10L);
        c.applyPlan("t", "d", type, complete ? "HIGH" : null, complete ? "LOW" : null, 1L, complete ? start : null,
                complete ? start.plus(1, ChronoUnit.HOURS) : null, complete ? "roll back" : null, Instant.now());
        c.setStatus(status, Instant.now());
        when(repo.findById(10L)).thenReturn(Optional.of(c));
        return c;
    }

    @Test void missingAssessmentListsEveryGap() {
        assertThat(ChangeService.missingAssessment(change("NORMAL", "DRAFT", false)))
                .containsExactly("riskLevel", "impact", "rollbackPlan", "plannedStart", "plannedEnd");
        assertThat(ChangeService.missingAssessment(change("NORMAL", "DRAFT", true))).isEmpty();
    }

    @Test void submittingIncompleteAssessmentIsRejected() {
        change("NORMAL", "ASSESSMENT", false);
        assertThatThrownBy(() -> service.changeStatus(cm, 10, "APPROVAL")).isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("riskLevel");
        verify(approvals, never()).openStep(any(), any(), any());
    }

    @Test void standardChangeSkipsApprovalAndIsScheduled() {
        Change c = change("STANDARD", "ASSESSMENT", true);
        when(approvals.stepsFor(c)).thenReturn(List.of());
        service.changeStatus(cm, 10, "APPROVAL");
        assertThat(c.getStatus()).isEqualTo("SCHEDULED");
        verify(approvals, never()).openStep(any(), any(), any());
    }

    @Test void normalChangeOpensFirstStepAndWaits() {
        Change c = change("NORMAL", "ASSESSMENT", true);
        when(approvals.stepsFor(c)).thenReturn(ChangePolicy.steps("NORMAL", "HIGH"));
        service.changeStatus(cm, 10, "APPROVAL");
        assertThat(c.getStatus()).isEqualTo("APPROVAL");
        verify(approvals).openStep(eq(c), eq(new ChangePolicy.Step(1, "CHANGE_MANAGER")), any());
    }

    @Test void illegalTransitionIsRejected() {
        change("NORMAL", "DRAFT", true);
        assertThatThrownBy(() -> service.changeStatus(cm, 10, "IMPLEMENTING")).isInstanceOf(BusinessRuleException.class);
    }

    @Test void planIsLockedAfterSubmission() {
        change("NORMAL", "APPROVAL", true);
        ChangeIn in = new ChangeIn("t", "d", "NORMAL", "LOW", "LOW", 1L, null, null, null);
        assertThatThrownBy(() -> service.update(cm, 10, in)).isInstanceOf(ConflictException.class);
    }

    @Test void onlyChangeManagerClosesAndOnlyOwnerTeamImplements() {
        Change c = change("NORMAL", "IMPLEMENTED", true);
        assertThatThrownBy(() -> service.changeStatus(tech, 10, "CLOSED")).isInstanceOf(ForbiddenException.class);
        service.changeStatus(cm, 10, "CLOSED");
        assertThat(c.getStatus()).isEqualTo("CLOSED");
        change("NORMAL", "SCHEDULED", true);
        assertThatThrownBy(() -> service.changeStatus(new CurrentUser(5, 1, Set.of("TECHNICIAN"), Set.of(9L), "x", "x"), 10, "IMPLEMENTING"))
                .isInstanceOf(ForbiddenException.class);
        service.changeStatus(tech, 10, "IMPLEMENTING");
    }

    @Test void employeesCannotCreateChanges() {
        ChangeIn in = new ChangeIn("t", "d", "NORMAL", null, null, null, null, null, null);
        assertThatThrownBy(() -> service.create(employee, in)).isInstanceOf(ForbiddenException.class);
    }
}
