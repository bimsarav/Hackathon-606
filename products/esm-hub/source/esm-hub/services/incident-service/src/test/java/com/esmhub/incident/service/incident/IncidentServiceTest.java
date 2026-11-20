package com.esmhub.incident.service.incident;

import static com.esmhub.incident.service.incident.TestFixtures.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirService;
import com.esmhub.directory.DirTeam;
import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.IncidentProperties;
import com.esmhub.incident.service.events.IncidentEvents;
import com.esmhub.incident.service.incident.IncidentDtos.*;
import com.esmhub.incident.service.problem.ProblemRepository;
import com.esmhub.incident.service.reference.AssignmentRule;
import com.esmhub.incident.service.reference.AssignmentRuleRepository;
import com.esmhub.incident.service.sla.SlaEngine;
import com.esmhub.incident.service.sla.SlaService;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

class IncidentServiceTest {
    IncidentRepository incidents = mock(IncidentRepository.class);
    IncidentCommentRepository comments = mock(IncidentCommentRepository.class);
    WorklogRepository worklogs = mock(WorklogRepository.class);
    IncidentEventRepository timeline = mock(IncidentEventRepository.class);
    IdempotencyKeyRepository idempotency = mock(IdempotencyKeyRepository.class);
    ProblemRepository problems = mock(ProblemRepository.class);
    AssignmentRuleRepository rules = mock(AssignmentRuleRepository.class);
    SlaService sla = mock(SlaService.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    IncidentEvents events = mock(IncidentEvents.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    MutableClock clock = new MutableClock(T0);
    IncidentService service;

    @BeforeEach
    void setUp() {
        service = new IncidentService(incidents, comments, worklogs, timeline, idempotency, problems, rules, workflow(), sla,
                directory, events, audit, new IncidentProperties(7, 3, 80, 1000, false), clock);
        when(incidents.nextId()).thenReturn(10L);
        when(incidents.save(any(Incident.class))).thenAnswer(a -> a.getArgument(0));
        when(comments.save(any(IncidentComment.class))).thenAnswer(a -> withId(a.getArgument(0)));
        when(sla.calendarForUser(anyLong())).thenReturn(SlaEngine.TWENTY_FOUR_SEVEN);
        when(sla.targetsFor(any())).thenReturn(new SlaEngine.Targets(30, 480, false));
    }

    static <T> T withId(T entity) {
        ReflectionTestUtils.setField(entity, "id", 1L);
        return entity;
    }

    Incident stored(Incident i) {
        when(incidents.findByIdAndCompanyId(i.getId(), COMPANY)).thenReturn(Optional.of(i));
        return i;
    }

    CreateIncident create(Integer priority) {
        return new CreateIncident("Printer broken", "Paper jam again", null, null, priority, "PORTAL", null);
    }

    // ---------- create ----------
    @Test
    void employeeCannotSelfPrioritise() {
        IncidentView v = service.create(user(3, "EMPLOYEE"), create(1), null);
        assertThat(v.priorityId()).isEqualTo(3);
        assertThat(v.status()).isEqualTo("NEW");
        assertThat(v.ticketNo()).isEqualTo("INC-000010");
    }

    @Test
    void deskAgentKeepsRequestedPriorityAndRoutesByFirstMatchingRule() {
        AssignmentRule miss = mock(AssignmentRule.class);
        AssignmentRule hit = mock(AssignmentRule.class);
        when(miss.matches(any(), eq(1))).thenReturn(false);
        when(hit.matches(any(), eq(1))).thenReturn(true);
        when(hit.getTeamId()).thenReturn(5L);
        when(rules.findByCompanyIdOrderBySortOrderAscIdAsc(COMPANY)).thenReturn(List.of(miss, hit));
        IncidentView v = service.create(user(2, "SERVICE_DESK_AGENT"), create(1), null);
        assertThat(v.priorityId()).isEqualTo(1);
        assertThat(v.assignedTeamId()).isEqualTo(5L);
    }

    @Test
    void routingFallsBackToTheServicesOwningTeam() {
        DirService svc = mock(DirService.class);
        when(svc.isActive()).thenReturn(true);
        when(svc.getOwningTeamId()).thenReturn(8L);
        when(directory.serviceInCompany(4L, COMPANY)).thenReturn(Optional.of(svc));
        when(directory.service(4L)).thenReturn(Optional.of(svc));
        IncidentView v = service.create(user(3, "EMPLOYEE"), new CreateIncident("Printer broken", "Paper jam", 4L, null, null, null, null), null);
        assertThat(v.assignedTeamId()).isEqualTo(8L);
        assertThat(v.channel()).isEqualTo("PORTAL");
    }

    @Test
    void unknownOrInactiveServiceIsNotFound() {
        assertThatThrownBy(() -> service.create(user(3, "EMPLOYEE"),
                new CreateIncident("Printer broken", "Paper jam", 99L, null, null, null, null), null))
                .isInstanceOf(NotFoundException.class);
    }

    @Test
    void employeeCannotLogOnBehalfOfAnotherUser() {
        assertThatThrownBy(() -> service.create(user(3, "EMPLOYEE"),
                new CreateIncident("Printer broken", "Paper jam", null, null, null, null, 9L), null))
                .isInstanceOf(ForbiddenException.class);
    }

    @Test
    void agentLogsOnBehalfOfRequesterOfTheSameCompanyOnly() {
        DirUser req = mock(DirUser.class);
        when(req.getUserId()).thenReturn(9L);
        when(directory.userInCompany(9L, COMPANY)).thenReturn(Optional.of(req));
        IncidentView v = service.create(user(2, "SERVICE_DESK_AGENT"),
                new CreateIncident("Printer broken", "Paper jam", null, null, null, null, 9L), null);
        assertThat(v.requesterId()).isEqualTo(9L);
        assertThatThrownBy(() -> service.create(user(2, "SERVICE_DESK_AGENT"),
                new CreateIncident("Printer broken", "Paper jam", null, null, null, null, 77L), null))
                .isInstanceOf(NotFoundException.class);
    }

    @Test
    void createPublishesSnapshotEventAndAudit() {
        service.create(user(3, "EMPLOYEE"), create(null), null);
        verify(events).snapshot(any(Incident.class));
        verify(events).domain(eq("incident.created"), any(), eq(Set.of(3L)), anyString(), anyString(), eq(true), any());
        verify(audit).record(eq("INCIDENT"), eq(10L), eq("CREATE"), isNull(), any());
    }

    @Test
    void idempotencyKeyReplaysTheFirstResult() {
        Incident existing = stored(incident(10, 3, null, null, 1, 3, T0));
        IdempotencyKey stored = new IdempotencyKey(new IdempotencyKey.Key(3L, "k1", "incidents.create"), 10L, T0);
        when(idempotency.findById(any())).thenReturn(Optional.of(stored));
        IncidentView v = service.create(user(3, "EMPLOYEE"), create(null), "k1");
        assertThat(v.id()).isEqualTo(existing.getId());
        verify(incidents, never()).save(any(Incident.class));
    }

    // ---------- visibility (BQ-3) ----------
    @Test
    void foreignCompanyAndForeignRequesterAreNotFound() {
        stored(incident(10, 3, 1L, null, 1, 3, T0));
        assertThatThrownBy(() -> service.get(user(4, "EMPLOYEE"), 10)).isInstanceOf(NotFoundException.class);
        assertThatThrownBy(() -> service.get(user(4, 2L, List.of(), "ADMIN"), 10)).isInstanceOf(NotFoundException.class);
        assertThat(service.get(user(3, "EMPLOYEE"), 10).id()).isEqualTo(10);
        assertThat(service.get(user(8, "AUDITOR"), 10).id()).isEqualTo(10);
    }

    @Test
    void technicianSeesOnlyOwnAndTeamIncidents() {
        stored(incident(10, 3, 1L, 6L, 3, 3, T0));
        assertThat(service.get(user(6, COMPANY, List.of(), "TECHNICIAN"), 10).canWork()).isTrue();
        assertThat(service.get(user(7, COMPANY, List.of(1L), "TECHNICIAN"), 10).canWork()).isTrue();
        assertThatThrownBy(() -> service.get(user(7, COMPANY, List.of(2L), "TECHNICIAN"), 10)).isInstanceOf(NotFoundException.class);
    }

    @Test
    void requesterDoesNotSeeInternalNotesOrWorklogs() {
        stored(incident(10, 3, 1L, null, 3, 3, T0));
        List<IncidentComment> existing = List.of(withId(new IncidentComment(10, 2, "public", false, T0)),
                withId(new IncidentComment(10, 2, "secret", true, T0)));
        when(comments.findByIncidentIdOrderByCreatedAtAscIdAsc(10L)).thenReturn(existing);
        assertThat(service.get(user(3, "EMPLOYEE"), 10).comments()).extracting(CommentView::body).containsExactly("public");
        assertThat(service.get(user(2, "SERVICE_DESK_AGENT"), 10).comments()).hasSize(2);
        assertThat(service.get(user(3, "EMPLOYEE"), 10).worklogs()).isEmpty();
    }

    // ---------- status workflow, SLA pause ----------
    @Test
    void invalidTransitionIsRejected() {
        stored(incident(10, 3, 1L, 2L, 1, 3, T0));
        assertThatThrownBy(() -> service.changeStatus(user(2, "SERVICE_DESK_AGENT"), 10, new ChangeStatus("RESOLVED", "FIXED", null)))
                .isInstanceOf(BusinessRuleException.class).hasMessageContaining("not allowed");
    }

    @Test
    void resolveNeedsResolutionCodeAndAssigneeOrLead() {
        Incident i = stored(incident(10, 3, 1L, 6L, 3, 3, T0));
        var tech = user(7, COMPANY, List.of(1L), "TECHNICIAN");
        assertThatThrownBy(() -> service.changeStatus(user(6, COMPANY, List.of(1L), "TECHNICIAN"), 10, new ChangeStatus("RESOLVED", null, null)))
                .isInstanceOf(BusinessRuleException.class).hasMessageContaining("resolution code");
        assertThatThrownBy(() -> service.changeStatus(tech, 10, new ChangeStatus("RESOLVED", "FIXED", null)))
                .isInstanceOf(ForbiddenException.class);
        service.changeStatus(user(6, COMPANY, List.of(1L), "TECHNICIAN"), 10, new ChangeStatus("RESOLVED", "FIXED", "swapped toner"));
        assertThat(i.getStatusId()).isEqualTo(5);
        assertThat(i.getResolvedAt()).isEqualTo(T0);
        assertThat(i.getResolutionCode()).isEqualTo("FIXED");
        verify(events).domain(eq("incident.status_changed"), eq(i), eq(Set.of(3L)), anyString(), anyString(), eq(true), any());
    }

    @Test
    void resolvingAfterDueDateMarksResolutionBreached() {
        Incident i = stored(incident(10, 3, 1L, 6L, 3, 3, T0));
        i.setDueDates(T0.plusSeconds(60), T0.plusSeconds(600));
        clock.set(T0.plusSeconds(3600));
        service.changeStatus(user(6, COMPANY, List.of(1L), "TECHNICIAN"), 10, new ChangeStatus("RESOLVED", "FIXED", null));
        assertThat(i.isResolutionBreached()).isTrue();
    }

    @Test
    void employeeCannotWorkOrCloseSomeoneElsesIncidentButRequesterCanCancel() {
        Incident i = stored(incident(10, 3, 1L, null, 1, 3, T0));
        assertThatThrownBy(() -> service.changeStatus(user(3, "EMPLOYEE"), 10, new ChangeStatus("IN_PROGRESS", null, null)))
                .isInstanceOf(ForbiddenException.class);
        service.changeStatus(user(3, "EMPLOYEE"), 10, new ChangeStatus("CANCELLED", null, null));
        assertThat(i.getStatusId()).isEqualTo(7);
        assertThat(i.getClosedAt()).isEqualTo(T0);
    }

    @Test
    void pendingUserPausesTheSlaClockAndResumeAccumulatesPausedMinutes() {
        Incident i = stored(incident(10, 3, 1L, 6L, 3, 3, T0));
        var tech = user(6, COMPANY, List.of(1L), "TECHNICIAN");
        service.changeStatus(tech, 10, new ChangeStatus("PENDING_USER", null, null));
        assertThat(i.getSlaPausedSince()).isEqualTo(T0);
        clock.set(T0.plus(Duration.ofMinutes(45)));
        service.changeStatus(tech, 10, new ChangeStatus("IN_PROGRESS", null, null));
        assertThat(i.getSlaPausedSince()).isNull();
        assertThat(i.getSlaPausedMinutes()).isEqualTo(45);
        assertThat(i.getFirstResponseAt()).isEqualTo(clock.instant());
        verify(sla).recompute(i);
        ArgumentCaptor<IncidentEvent> ev = ArgumentCaptor.forClass(IncidentEvent.class);
        verify(timeline, atLeastOnce()).save(ev.capture());
        assertThat(ev.getAllValues()).extracting(IncidentEvent::getEventType).contains("SLA_PAUSE", "SLA_RESUME", "STATUS_CHANGE");
    }

    @Test
    void closedIncidentsCannotBeEditedOrAssigned() {
        stored(incident(10, 3, 1L, 6L, 6, 3, T0));
        assertThatThrownBy(() -> service.update(user(3, "EMPLOYEE"), 10, new UpdateIncident("New title", null, null, null, null)))
                .isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> service.assign(user(2, "SERVICE_DESK_AGENT"), 10, new Assign(1L, 6L)))
                .isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void onlyDeskStaffChangePriorityAndTheSlaIsRecomputed() {
        Incident i = stored(incident(10, 3, 1L, null, 1, 3, T0));
        assertThatThrownBy(() -> service.update(user(3, "EMPLOYEE"), 10, new UpdateIncident(null, null, null, 1, null)))
                .isInstanceOf(ForbiddenException.class);
        service.update(user(2, "SERVICE_DESK_AGENT"), 10, new UpdateIncident(null, null, null, 1, null));
        assertThat(i.getPriorityId()).isEqualTo(1);
        verify(sla).apply(i);
    }

    // ---------- assignment ----------
    DirTeam team(boolean active, Set<Long> members) {
        DirTeam t = mock(DirTeam.class);
        when(t.isActive()).thenReturn(active);
        return t;
    }

    @Test
    void assigneeMustBeATeamMemberWithAResolverRole() {
        Incident i = stored(incident(10, 3, 1L, null, 1, 3, T0));
        DirUser u = mock(DirUser.class);
        DirTeam t = team(true, Set.of());
        when(directory.teamInCompany(1L, COMPANY)).thenReturn(Optional.of(t));
        when(directory.userInCompany(6L, COMPANY)).thenReturn(Optional.of(u));
        var agent = user(2, "SERVICE_DESK_AGENT");
        when(directory.isMember(1L, 6L)).thenReturn(false);
        assertThatThrownBy(() -> service.assign(agent, 10, new Assign(1L, 6L))).isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("member");
        when(directory.isMember(1L, 6L)).thenReturn(true);
        when(u.getRoles()).thenReturn(Set.of("EMPLOYEE"));
        assertThatThrownBy(() -> service.assign(agent, 10, new Assign(1L, 6L))).isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("resolver role");
        when(u.getRoles()).thenReturn(Set.of("EMPLOYEE", "TECHNICIAN"));
        service.assign(agent, 10, new Assign(1L, 6L));
        assertThat(i.getAssignedUserId()).isEqualTo(6L);
        assertThat(i.getStatusId()).isEqualTo(2); // NEW moves to ASSIGNED
        verify(events).domain(eq("incident.assigned"), eq(i), eq(Set.of(6L)), anyString(), anyString(), eq(true), any());
    }

    @Test
    void employeeCannotAssignAndTechnicianMaySelfAssign() {
        Incident i = stored(incident(10, 3, 1L, null, 1, 3, T0));
        assertThatThrownBy(() -> service.assign(user(3, "EMPLOYEE"), 10, new Assign(1L, 3L))).isInstanceOf(ForbiddenException.class);
        DirUser u = mock(DirUser.class);
        when(u.getRoles()).thenReturn(Set.of("TECHNICIAN"));
        DirTeam t = team(true, Set.of());
        when(directory.teamInCompany(1L, COMPANY)).thenReturn(Optional.of(t));
        when(directory.userInCompany(6L, COMPANY)).thenReturn(Optional.of(u));
        when(directory.isMember(1L, 6L)).thenReturn(true);
        service.assign(user(6, COMPANY, List.of(1L), "TECHNICIAN"), 10, new Assign(null, 6L));
        assertThat(i.getAssignedUserId()).isEqualTo(6L);
    }

    // ---------- reopen (BQ-4) ----------
    @Test
    void reopenOnlyResolvedWithinWindowByRequesterOrDesk() {
        Incident closed = stored(incident(11, 3, 1L, 6L, 6, 3, T0));
        assertThatThrownBy(() -> service.reopen(user(3, "EMPLOYEE"), 11, new Reopen("still broken")))
                .isInstanceOf(BusinessRuleException.class).hasMessageContaining("Only resolved");

        Incident i = stored(incident(10, 3, 1L, 6L, 5, 3, T0));
        i.setResolvedAt(T0);
        assertThatThrownBy(() -> service.reopen(user(4, "EMPLOYEE"), 10, new Reopen("still broken")))
                .isInstanceOf(NotFoundException.class);
        clock.set(T0.plus(Duration.ofDays(8)));
        assertThatThrownBy(() -> service.reopen(user(3, "EMPLOYEE"), 10, new Reopen("still broken")))
                .isInstanceOf(BusinessRuleException.class).hasMessageContaining("window");
        clock.set(T0.plus(Duration.ofDays(6)));
        service.reopen(user(3, "EMPLOYEE"), 10, new Reopen("still broken"));
        assertThat(i.getStatusId()).isEqualTo(3);
        assertThat(i.getReopenedCount()).isEqualTo(1);
        assertThat(i.getResolvedAt()).isNull();
        assertThat(closed.getStatusId()).isEqualTo(6);
        verify(events).domain(eq("incident.reopened"), eq(i), any(), anyString(), eq("still broken"), eq(true), any());
    }

    // ---------- comments, worklogs, rating ----------
    @Test
    void internalNotesAreForResolversAndClosedIncidentsRejectComments() {
        Incident i = stored(incident(10, 3, 1L, null, 3, 3, T0));
        assertThatThrownBy(() -> service.comment(user(3, "EMPLOYEE"), 10, new AddComment("psst", true))).isInstanceOf(ForbiddenException.class);
        assertThatThrownBy(() -> service.comment(user(5, COMPANY, List.of(), "TECHNICIAN"), 10, new AddComment("hi", false)))
                .isInstanceOf(NotFoundException.class);
        service.comment(user(2, "SERVICE_DESK_AGENT"), 10, new AddComment("working on it", false));
        assertThat(i.getFirstResponseAt()).isEqualTo(T0); // a public reply from a resolver is the first response
        verify(events).domain(eq("incident.commented"), eq(i), eq(Set.of(3L)), anyString(), anyString(), eq(true), any());
        i.setStatusId(6);
        assertThatThrownBy(() -> service.comment(user(3, "EMPLOYEE"), 10, new AddComment("thanks", false)))
                .isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void worklogsRequireWorkRights() {
        stored(incident(10, 3, 1L, null, 3, 3, T0));
        assertThatThrownBy(() -> service.worklog(user(3, "EMPLOYEE"), 10, new AddWorklog(30, "fixing"))).isInstanceOf(ForbiddenException.class);
        when(worklogs.save(any(Worklog.class))).thenAnswer(a -> withId(a.getArgument(0)));
        WorklogView w = service.worklog(user(2, "SERVICE_DESK_AGENT"), 10, new AddWorklog(30, "fixing"));
        assertThat(w.minutesSpent()).isEqualTo(30);
        verify(events).snapshot(any(Incident.class));
    }

    @Test
    void onlyTheRequesterRatesAResolvedIncident() {
        Incident i = stored(incident(10, 3, 1L, 6L, 3, 3, T0));
        assertThatThrownBy(() -> service.rate(user(3, "EMPLOYEE"), 10, 5)).isInstanceOf(BusinessRuleException.class);
        i.setStatusId(5);
        assertThatThrownBy(() -> service.rate(user(2, "SERVICE_DESK_AGENT"), 10, 5)).isInstanceOf(ForbiddenException.class);
        service.rate(user(3, "EMPLOYEE"), 10, 4);
        assertThat(i.getSatisfactionScore()).isEqualTo(4);
    }

    @Test
    void exportIsRestrictedToStaffAndAuditors() {
        assertThatThrownBy(() -> service.export(user(3, "EMPLOYEE"), new IncidentService.Filter(null, null, null, null, null, null, "all", false, "created")))
                .isInstanceOf(ForbiddenException.class);
    }
}
