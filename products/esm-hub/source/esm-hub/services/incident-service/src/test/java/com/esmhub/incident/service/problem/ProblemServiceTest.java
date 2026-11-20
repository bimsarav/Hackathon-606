package com.esmhub.incident.service.problem;

import static com.esmhub.incident.service.incident.TestFixtures.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirTeam;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.events.IncidentEvents;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.incident.IncidentRepository;
import com.esmhub.incident.service.problem.ProblemDtos.*;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ProblemServiceTest {
    ProblemRepository problems = mock(ProblemRepository.class);
    IncidentRepository incidents = mock(IncidentRepository.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    IncidentEvents events = mock(IncidentEvents.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    ProblemService service;
    Problem problem;
    CurrentUser agent = user(2, "SERVICE_DESK_AGENT");

    @BeforeEach
    void setUp() {
        service = new ProblemService(problems, incidents, workflow(), directory, events, audit, new MutableClock(T0));
        problem = new Problem(5L, COMPANY, "Recurring VPN drops", "desc", null, T0);
        when(problems.findByIdAndCompanyId(5L, COMPANY)).thenReturn(Optional.of(problem));
        when(problems.nextId()).thenReturn(6L);
        when(problems.save(any(Problem.class))).thenAnswer(a -> a.getArgument(0));
    }

    UpdateProblem status(String s) { return new UpdateProblem(null, null, s, null, null, null); }

    @Test
    void createsWithNumberLinksAndSnapshot() {
        Incident i = incident(10, 3, 1L, null, 1, 3, T0);
        when(incidents.findByIdAndCompanyId(10L, COMPANY)).thenReturn(Optional.of(i));
        when(incidents.findAllById(any())).thenReturn(List.of(i));
        ProblemView v = service.create(agent, new CreateProblem("Recurring VPN drops", null, null, List.of(10L)));
        assertThat(v.problemNo()).isEqualTo("PRB-00006");
        assertThat(v.status()).isEqualTo("OPEN");
        assertThat(v.incidentCount()).isEqualTo(1);
        assertThat(v.incidents()).extracting(IncidentRef::ticketNo).containsExactly("INC-000010");
        verify(events).snapshot(any(Problem.class));
        verify(audit).record(org.mockito.ArgumentMatchers.eq("PROBLEM"), org.mockito.ArgumentMatchers.eq(6L),
                org.mockito.ArgumentMatchers.eq("CREATE"), org.mockito.ArgumentMatchers.isNull(), any());
    }

    @Test
    void linkingAForeignIncidentIsNotFound() {
        assertThatThrownBy(() -> service.linkIncidents(agent, 5, List.of(99L))).isInstanceOf(NotFoundException.class);
    }

    @Test
    void employeesCannotReadOrWriteButAuditorsCanRead() {
        assertThatThrownBy(() -> service.get(user(3, "EMPLOYEE"), 5)).isInstanceOf(ForbiddenException.class);
        assertThatThrownBy(() -> service.create(user(3, "EMPLOYEE"), new CreateProblem("title", null, null, null)))
                .isInstanceOf(ForbiddenException.class);
        assertThatThrownBy(() -> service.update(user(8, "AUDITOR"), 5, status("INVESTIGATING"))).isInstanceOf(ForbiddenException.class);
        when(incidents.findAllById(any())).thenReturn(List.of());
        assertThat(service.get(user(8, "AUDITOR"), 5).id()).isEqualTo(5);
    }

    @Test
    void foreignCompanyProblemIsNotFound() {
        assertThatThrownBy(() -> service.get(user(2, 2L, List.of(), "ADMIN"), 5)).isInstanceOf(NotFoundException.class);
    }

    @Test
    void workflowRejectsSkippedStates() {
        assertThatThrownBy(() -> service.update(agent, 5, status("RESOLVED"))).isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("not allowed");
        assertThatThrownBy(() -> service.update(agent, 5, status("KNOWN_ERROR"))).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void knownErrorNeedsWorkaroundAndResolveNeedsRootCause() {
        service.update(agent, 5, status("INVESTIGATING"));
        assertThatThrownBy(() -> service.update(agent, 5, status("KNOWN_ERROR"))).isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("workaround");
        service.update(agent, 5, new UpdateProblem(null, null, "KNOWN_ERROR", null, "Reconnect VPN", null));
        assertThat(problem.isKnownError()).isTrue();
        assertThatThrownBy(() -> service.update(agent, 5, status("RESOLVED"))).isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("root cause");
        service.update(agent, 5, new UpdateProblem(null, null, "RESOLVED", "Firewall idle timeout", null, null));
        assertThat(problem.getStatus()).isEqualTo("RESOLVED");
        assertThat(problem.getResolvedAt()).isEqualTo(T0);
        service.update(agent, 5, status("INVESTIGATING")); // reopening clears the resolution date
        assertThat(problem.getResolvedAt()).isNull();
    }

    @Test
    void closedProblemsStayClosed() {
        service.update(agent, 5, status("CLOSED"));
        assertThatThrownBy(() -> service.update(agent, 5, status("INVESTIGATING"))).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void unlinkRemovesTheLinkOrIs404() {
        problem.link(10);
        service.unlink(agent, 5, 10);
        assertThat(problem.getIncidentIds()).isEmpty();
        assertThatThrownBy(() -> service.unlink(agent, 5, 10)).isInstanceOf(NotFoundException.class);
    }

    @Test
    void ownerTeamMustBelongToTheCompany() {
        when(directory.teamInCompany(anyLong(), anyLong())).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.create(agent, new CreateProblem("title", null, 99L, null))).isInstanceOf(NotFoundException.class);
        DirTeam t = mock(DirTeam.class);
        when(directory.teamInCompany(3L, COMPANY)).thenReturn(Optional.of(t));
        service.update(agent, 5, new UpdateProblem(null, null, null, null, null, 3L));
        assertThat(problem.getOwnerTeamId()).isEqualTo(3L);
    }
}
