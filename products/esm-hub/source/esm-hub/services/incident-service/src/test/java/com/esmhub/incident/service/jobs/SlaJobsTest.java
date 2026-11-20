package com.esmhub.incident.service.jobs;

import static com.esmhub.incident.service.incident.TestFixtures.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.IncidentProperties;
import com.esmhub.incident.service.events.IncidentEvents;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.incident.IncidentEvent;
import com.esmhub.incident.service.incident.IncidentEventRepository;
import com.esmhub.incident.service.incident.IncidentRepository;
import com.esmhub.incident.service.reference.EscalationRule;
import com.esmhub.incident.service.reference.EscalationRuleRepository;
import com.esmhub.incident.service.sla.SlaEngine;
import com.esmhub.incident.service.sla.SlaService;
import java.time.Duration;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.JdbcTemplate;

class SlaJobsTest {
    IncidentRepository incidents = mock(IncidentRepository.class);
    IncidentEventRepository timeline = mock(IncidentEventRepository.class);
    EscalationRuleRepository escalationRules = mock(EscalationRuleRepository.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    SlaService sla = mock(SlaService.class);
    IncidentEvents events = mock(IncidentEvents.class);
    JdbcTemplate jdbc = mock(JdbcTemplate.class);
    MutableClock clock = new MutableClock(T0);
    SlaJobs jobs;

    @BeforeEach
    void setUp() {
        jobs = new SlaJobs(incidents, timeline, escalationRules, directory, sla, workflow(), events,
                new IncidentProperties(7, 3, 80, 1000, false), jdbc, clock);
        when(sla.calendarForUser(anyLong())).thenReturn(SlaEngine.TWENTY_FOUR_SEVEN);
        when(sla.targetsFor(any())).thenReturn(new SlaEngine.Targets(30, 480, false));
        when(jdbc.update(anyString(), any(), any(), any())).thenReturn(1);
    }

    EscalationRule rule(String role, boolean assignee) {
        EscalationRule r = mock(EscalationRule.class);
        when(r.getNotifyRole()).thenReturn(role);
        when(r.isNotifyAssignee()).thenReturn(assignee);
        return r;
    }

    Incident open() {
        Incident i = incident(10, 3, 1L, 6L, 3, 2, T0);
        i.setDueDates(T0.plus(Duration.ofMinutes(30)), T0.plus(Duration.ofMinutes(480)));
        return i;
    }

    @Test
    void flagsBreachesAndEscalatesToLeadsRoleHoldersAndAssignee() {
        Incident i = open();
        when(incidents.lockOpenWithSla()).thenReturn(List.of(i));
        clock.set(T0.plus(Duration.ofMinutes(600)));
        EscalationRule lead = rule("TEAM_LEAD", true);
        EscalationRule manager = rule("SERVICE_MANAGER", false);
        when(escalationRules.matching(anyLong(), anyInt(), anyString())).thenReturn(List.of(lead, manager));
        when(directory.teamLead(1L)).thenReturn(Set.of(20L));
        when(directory.activeUserIdsWithRole(1L, "SERVICE_MANAGER")).thenReturn(Set.of(30L));
        assertThat(jobs.scanSla()).isEqualTo(1);
        assertThat(i.isResponseBreached()).isTrue();
        assertThat(i.isResolutionBreached()).isTrue();
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Set<Long>> to = (ArgumentCaptor<Set<Long>>) (ArgumentCaptor<?>) ArgumentCaptor.forClass(Set.class);
        verify(events, times(2)).domain(eq("incident.sla_escalated"), eq(i), to.capture(), anyString(), anyString(), eq(true), any());
        assertThat(to.getValue()).containsExactlyInAnyOrder(20L, 30L, 6L);
        verify(events).snapshot(i);
        verify(timeline, times(2)).save(any(IncidentEvent.class));
    }

    @Test
    void secondScanDoesNotEscalateAgain() {
        Incident i = open();
        i.setResponseBreached(true);
        i.setResolutionBreached(true);
        when(incidents.lockOpenWithSla()).thenReturn(List.of(i));
        clock.set(T0.plus(Duration.ofMinutes(600)));
        assertThat(jobs.scanSla()).isZero();
        verifyNoInteractions(events);
    }

    @Test
    void concurrentReplicaWinsTheDedupeInsert() {
        Incident i = open();
        when(incidents.lockOpenWithSla()).thenReturn(List.of(i));
        when(jdbc.update(anyString(), any(), any(), any())).thenReturn(0); // primary key conflict: already escalated
        clock.set(T0.plus(Duration.ofMinutes(600)));
        jobs.scanSla();
        verify(events, never()).domain(anyString(), any(), any(), anyString(), anyString(), anyBoolean(), any());
    }

    @Test
    void atRiskEscalatesOnceAtEightyPercentWithoutFlagging() {
        Incident i = open();
        i.setFirstResponseAt(T0);
        when(incidents.lockOpenWithSla()).thenReturn(List.of(i));
        EscalationRule lead = rule("TEAM_LEAD", false);
        when(escalationRules.matching(1L, 2, "RESOLUTION_AT_RISK")).thenReturn(List.of(lead));
        when(directory.teamLead(1L)).thenReturn(Set.of(20L));
        clock.set(T0.plus(Duration.ofMinutes(390))); // 81% of 480
        assertThat(jobs.scanSla()).isZero();
        assertThat(i.isResolutionBreached()).isFalse();
        verify(events).domain(eq("incident.sla_escalated"), eq(i), eq(Set.of(20L)), anyString(), anyString(), eq(true), any());
        clock.set(T0.plus(Duration.ofMinutes(100))); // 21%: nothing
        reset(events);
        jobs.scanSla();
        verifyNoInteractions(events);
    }

    @Test
    void pausedIncidentsOnlyGetResponseChecks() {
        Incident i = open();
        i.setFirstResponseAt(T0);
        i.setSlaPausedSince(T0);
        when(incidents.lockOpenWithSla()).thenReturn(List.of(i));
        clock.set(T0.plus(Duration.ofMinutes(600)));
        assertThat(jobs.scanSla()).isZero();
        assertThat(i.isResolutionBreached()).isFalse();
    }

    @Test
    void autoCloseClosesResolvedIncidentsPastTheCutoff() {
        Incident i = incident(10, 3, 1L, 6L, 5, 2, T0);
        i.setResolvedAt(T0);
        clock.set(T0.plus(Duration.ofDays(4)));
        when(incidents.lockResolvedBefore(eq(5), eq(clock.instant().minus(Duration.ofDays(3))))).thenReturn(List.of(i));
        assertThat(jobs.autoClose()).isEqualTo(1);
        assertThat(i.getStatusId()).isEqualTo(6);
        assertThat(i.getClosedAt()).isEqualTo(clock.instant());
        verify(events).snapshot(i);
        ArgumentCaptor<IncidentEvent> ev = ArgumentCaptor.forClass(IncidentEvent.class);
        verify(timeline).save(ev.capture());
        assertThat(ev.getValue().getActorId()).isNull();
        assertThat(ev.getValue().getToValue()).isEqualTo("CLOSED");
    }

    @Test
    void autoCloseWithNothingDueDoesNothing() {
        when(incidents.lockResolvedBefore(anyInt(), any())).thenReturn(List.of());
        assertThat(jobs.autoClose()).isZero();
        verifyNoInteractions(events);
    }
}
