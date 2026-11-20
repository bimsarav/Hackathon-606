package com.esmhub.incident.service.incident;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.incident.service.reference.Priority;
import com.esmhub.incident.service.reference.PriorityRepository;
import com.esmhub.incident.service.reference.StatusTransition;
import com.esmhub.incident.service.reference.StatusTransitionRepository;
import com.esmhub.incident.service.reference.TicketStatus;
import com.esmhub.incident.service.reference.TicketStatusRepository;
import com.esmhub.incident.service.reference.Workflow;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Set;

/** Shared builders for the unit tests: the real workflow rules over mocked reference repositories. */
public final class TestFixtures {
    private TestFixtures() {}

    public static final long COMPANY = 1L;
    public static final Instant T0 = Instant.parse("2026-11-16T05:00:00Z");

    /** A clock the test can move. */
    public static final class MutableClock extends Clock {
        private Instant now;

        public MutableClock(Instant now) { this.now = now; }

        public void set(Instant t) { now = t; }

        @Override public java.time.ZoneId getZone() { return ZoneOffset.UTC; }
        @Override public Clock withZone(java.time.ZoneId zone) { return this; }
        @Override public Instant instant() { return now; }
    }

    public static CurrentUser user(long id, long company, List<Long> teams, String... roles) {
        return new CurrentUser(id, company, Set.of(roles), Set.copyOf(teams), "User " + id, "u" + id + "@example.test");
    }

    public static CurrentUser user(long id, String... roles) { return user(id, COMPANY, List.of(), roles); }

    public static Workflow workflow() {
        List<TicketStatus> all = List.of(new TicketStatus(1, "NEW", false, false), new TicketStatus(2, "ASSIGNED", false, false),
                new TicketStatus(3, "IN_PROGRESS", false, false), new TicketStatus(4, "PENDING_USER", false, true),
                new TicketStatus(5, "RESOLVED", true, false), new TicketStatus(6, "CLOSED", true, false),
                new TicketStatus(7, "CANCELLED", true, false));
        TicketStatusRepository statuses = mock(TicketStatusRepository.class);
        when(statuses.findAll()).thenReturn(all);
        when(statuses.findByName(any())).thenAnswer(a -> all.stream().filter(s -> s.getName().equals(a.getArgument(0))).findFirst());
        when(statuses.findById(any())).thenAnswer(a -> all.stream().filter(s -> s.getId().equals(a.getArgument(0))).findFirst());
        int[][] allowed = {{1, 2}, {1, 3}, {1, 7}, {2, 3}, {2, 4}, {2, 5}, {2, 7}, {3, 2}, {3, 4}, {3, 5}, {4, 3}, {4, 5}, {4, 7}, {5, 6}, {5, 3}};
        List<StatusTransition> transitions = java.util.Arrays.stream(allowed).map(p -> {
            StatusTransition t = mock(StatusTransition.class);
            when(t.getId()).thenReturn(new StatusTransition.Key(p[0], p[1]));
            return t;
        }).toList();
        StatusTransitionRepository tr = mock(StatusTransitionRepository.class);
        when(tr.findAll()).thenReturn(transitions);
        when(tr.existsById(any())).thenAnswer(a -> {
            StatusTransition.Key k = a.getArgument(0);
            return java.util.Arrays.stream(allowed).anyMatch(p -> p[0] == k.fromStatusId() && p[1] == k.toStatusId());
        });
        PriorityRepository pr = mock(PriorityRepository.class);
        when(pr.findAll()).thenReturn(List.of(new Priority(1, "P1", 15, 240), new Priority(2, "P2", 30, 480),
                new Priority(3, "P3", 240, 2880), new Priority(4, "P4", 480, 5760)));
        return new Workflow(statuses, tr, pr);
    }

    public static Incident incident(long id, long requester, Long team, Long assignee, int statusId, int priority, Instant created) {
        Incident i = new Incident(id, COMPANY, "Printer broken", "details", requester, null, null, priority, statusId, team,
                "PORTAL", created);
        i.assignTo(team, assignee);
        return i;
    }
}
