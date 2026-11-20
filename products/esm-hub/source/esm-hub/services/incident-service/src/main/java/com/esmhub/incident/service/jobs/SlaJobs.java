package com.esmhub.incident.service.jobs;

import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.IncidentProperties;
import com.esmhub.incident.service.events.IncidentEvents;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.incident.IncidentEvent;
import com.esmhub.incident.service.incident.IncidentEventRepository;
import com.esmhub.incident.service.incident.IncidentRepository;
import com.esmhub.incident.service.reference.EscalationRule;
import com.esmhub.incident.service.reference.EscalationRuleRepository;
import com.esmhub.incident.service.reference.TicketStatus;
import com.esmhub.incident.service.reference.Workflow;
import com.esmhub.incident.service.sla.SlaEngine;
import com.esmhub.incident.service.sla.SlaService;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Scheduled business rules (ADR-0005): SLA breach flags with escalation (once per incident and trigger, enforced by the
 * primary key of incident_escalations, so replicas and repeated scans never notify twice) and BQ-4 auto-close.
 * Rows are locked with SKIP LOCKED, several replicas can run these safely.
 */
@Component
public class SlaJobs {
    private final IncidentRepository incidents;
    private final IncidentEventRepository timeline;
    private final EscalationRuleRepository escalationRules;
    private final DirectoryLookup directory;
    private final SlaService sla;
    private final Workflow workflow;
    private final IncidentEvents events;
    private final IncidentProperties props;
    private final JdbcTemplate jdbc;
    private final Clock clock;

    public SlaJobs(IncidentRepository incidents, IncidentEventRepository timeline, EscalationRuleRepository escalationRules,
                   DirectoryLookup directory, SlaService sla, Workflow workflow, IncidentEvents events,
                   IncidentProperties props, JdbcTemplate jdbc, Clock clock) {
        this.incidents = incidents;
        this.timeline = timeline;
        this.escalationRules = escalationRules;
        this.directory = directory;
        this.sla = sla;
        this.workflow = workflow;
        this.events = events;
        this.props = props;
        this.jdbc = jdbc;
        this.clock = clock;
    }

    /** Flags breaches and escalates once per trigger. Returns the number of incidents whose breach flags changed. */
    @Transactional
    public int scanSla() {
        Instant now = clock.instant();
        int changed = 0;
        for (Incident inc : incidents.lockOpenWithSla()) {
            boolean dirty = false;
            if (inc.getFirstResponseAt() == null && inc.getResponseDueAt() != null && now.isAfter(inc.getResponseDueAt())
                    && !inc.isResponseBreached()) {
                inc.setResponseBreached(true);
                escalate(inc, EscalationRule.RESPONSE_BREACH, "response SLA breached");
                dirty = true;
            }
            if (inc.getSlaPausedSince() == null) {
                if (now.isAfter(inc.getDueAt())) {
                    if (!inc.isResolutionBreached()) {
                        inc.setResolutionBreached(true);
                        escalate(inc, EscalationRule.RESOLUTION_BREACH, "resolution SLA breached");
                        dirty = true;
                    }
                } else {
                    SlaEngine.Targets targets = sla.targetsFor(inc);
                    SlaEngine.Calendar cal = sla.calendarForUser(inc.getRequesterId());
                    if (SlaEngine.resolutionProgressPct(inc.getCreatedAt(), now, targets, cal, inc.getSlaPausedMinutes())
                            >= props.atRiskPct()) {
                        escalate(inc, EscalationRule.RESOLUTION_AT_RISK, props.atRiskPct() + "% of resolution time used");
                    }
                }
            }
            if (dirty) {
                events.snapshot(inc);
                changed++;
            }
        }
        return changed;
    }

    private void escalate(Incident inc, String trigger, String subject) {
        Instant now = clock.instant();
        int inserted = jdbc.update("INSERT INTO incident_escalations (incident_id, trigger_type, escalated_at) VALUES (?, ?, ?) "
                + "ON CONFLICT DO NOTHING", inc.getId(), trigger, java.sql.Timestamp.from(now));
        if (inserted == 0) return; // already escalated for this trigger
        Set<Long> recipients = new HashSet<>();
        boolean assignee = false;
        List<EscalationRule> rules = escalationRules.matching(inc.getCompanyId(), inc.getPriorityId(), trigger);
        for (EscalationRule r : rules) {
            recipients.addAll("TEAM_LEAD".equals(r.getNotifyRole()) ? directory.teamLead(inc.getAssignedTeamId())
                    : directory.activeUserIdsWithRole(inc.getCompanyId(), r.getNotifyRole()));
            assignee |= r.isNotifyAssignee();
        }
        if (assignee && inc.getAssignedUserId() != null) recipients.add(inc.getAssignedUserId());
        timeline.save(new IncidentEvent(inc.getId(), "SLA_ESCALATED", null, null, trigger, now));
        events.domain("incident.sla_escalated", inc, recipients,
                "[" + trigger.replace('_', ' ') + "] " + inc.getTicketNo() + ": " + subject, inc.getTitle(), true,
                Map.of("trigger", trigger));
    }

    /** BQ-4: incidents resolved more than autoCloseDays ago are closed by the system. Returns how many. */
    @Transactional
    public int autoClose() {
        Instant now = clock.instant();
        Instant cutoff = now.minus(Duration.ofDays(props.autoCloseDays()));
        TicketStatus resolved = workflow.status(TicketStatus.RESOLVED);
        TicketStatus closed = workflow.status(TicketStatus.CLOSED);
        List<Incident> rows = incidents.lockResolvedBefore(resolved.getId(), cutoff);
        for (Incident inc : rows) {
            inc.setStatusId(closed.getId());
            inc.setClosedAt(now);
            inc.touch(now);
            timeline.save(new IncidentEvent(inc.getId(), "STATUS_CHANGE", null, TicketStatus.RESOLVED, TicketStatus.CLOSED, now));
            events.snapshot(inc);
            events.domain("incident.status_changed", inc, Set.of(), inc.getTicketNo() + " closed automatically", inc.getTitle(),
                    false, Map.of("to", TicketStatus.CLOSED, "automatic", true));
        }
        return rows.size();
    }
}
