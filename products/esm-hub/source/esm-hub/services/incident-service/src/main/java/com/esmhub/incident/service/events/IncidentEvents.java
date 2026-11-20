package com.esmhub.incident.service.events;

import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.IncidentSnapshot;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.common.contracts.DomainContracts.ProblemSnapshot;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.incident.WorklogRepository;
import com.esmhub.incident.service.problem.Problem;
import com.esmhub.incident.service.reference.Priority;
import com.esmhub.incident.service.reference.TicketStatus;
import com.esmhub.incident.service.reference.Workflow;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.springframework.stereotype.Component;

/** Builds state snapshots and domain events; everything goes through the outbox in the caller's transaction. */
@Component
public class IncidentEvents {
    private final OutboxPublisher outbox;
    private final Workflow workflow;
    private final WorklogRepository worklogs;

    public IncidentEvents(OutboxPublisher outbox, Workflow workflow, WorklogRepository worklogs) {
        this.outbox = outbox;
        this.workflow = workflow;
        this.worklogs = worklogs;
    }

    public static IncidentSnapshot toSnapshot(Incident i, TicketStatus status, Priority priority, long worklogMinutes) {
        return new IncidentSnapshot(i.getId(), i.getCompanyId(), i.getTicketNo(), i.getTitle(), status.getName(),
                status.isClosed(), priority.getName(), i.getServiceId(), i.getChannel(), i.getRequesterId(),
                i.getAssignedTeamId(), i.getAssignedUserId(), i.getCreatedAt(), i.getFirstResponseAt(), i.getResolvedAt(),
                i.getClosedAt(), i.getResponseDueAt(), i.getDueAt(), i.isResponseBreached(), i.isResolutionBreached(),
                i.getSlaPausedSince() != null, i.getReopenedCount(), i.getSatisfactionScore(), (int) worklogMinutes);
    }

    /** State snapshot after every change of an incident (compacted topic, key = incident id). */
    public void snapshot(Incident i) {
        TicketStatus status = workflow.status(i.getStatusId());
        Priority priority = workflow.prioritiesById().get(i.getPriorityId());
        outbox.publish(Topics.INCIDENT_INCIDENTS, "incident.snapshot", "INCIDENT", i.getId(), i.getCompanyId(),
                toSnapshot(i, status, priority, worklogs.totalMinutes(i.getId())));
    }

    public void snapshot(Problem p) {
        outbox.publish(Topics.INCIDENT_PROBLEMS, "problem.snapshot", "PROBLEM", p.getId(), p.getCompanyId(),
                new ProblemSnapshot(p.getId(), p.getCompanyId(), p.getProblemNo(), p.getTitle(), p.getStatus(),
                        p.isKnownError(), p.getOwnerTeamId(), p.getCreatedAt(), p.getResolvedAt(),
                        new ArrayList<>(new TreeSet<>(p.getIncidentIds()))));
    }

    /** Domain event with its notification intent (recipients are computed here, notification-service stays generic). */
    public void domain(String type, Incident i, Set<Long> recipients, String subject, String message, boolean email,
                       Map<String, Object> facts) {
        Map<String, Object> f = new LinkedHashMap<>(facts);
        f.putIfAbsent("status", workflow.status(i.getStatusId()).getName());
        f.putIfAbsent("priorityId", i.getPriorityId());
        var intent = new NotificationIntent(recipients.stream().filter(java.util.Objects::nonNull).sorted().toList(),
                subject, message, "/incidents/" + i.getId(), email);
        outbox.publish(Topics.INCIDENT_EVENTS, type, "INCIDENT", i.getId(), i.getCompanyId(),
                new DomainEvent("INCIDENT", String.valueOf(i.getId()), i.getTicketNo(), intent, f));
    }
}
