package com.esmhub.incident.service.problem;

import static com.esmhub.common.security.Role.*;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.events.IncidentEvents;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.incident.IncidentRepository;
import com.esmhub.incident.service.problem.ProblemDtos.*;
import com.esmhub.incident.service.reference.Workflow;
import java.time.Clock;
import java.time.Instant;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Problem management (FR-7): known errors, root cause, linked incidents. */
@Service
public class ProblemService {
    static final Role[] READERS = {SERVICE_DESK_AGENT, TECHNICIAN, TEAM_LEAD, SERVICE_MANAGER, CHANGE_MANAGER, AUDITOR, ADMIN};
    static final Role[] WRITERS = {SERVICE_DESK_AGENT, TECHNICIAN, TEAM_LEAD, SERVICE_MANAGER};
    static final Map<String, Set<String>> FLOW = Map.of(
            Problem.OPEN, Set.of(Problem.INVESTIGATING, Problem.CLOSED),
            Problem.INVESTIGATING, Set.of(Problem.KNOWN_ERROR, Problem.RESOLVED),
            Problem.KNOWN_ERROR, Set.of(Problem.RESOLVED),
            Problem.RESOLVED, Set.of(Problem.CLOSED, Problem.INVESTIGATING),
            Problem.CLOSED, Set.of());

    private final ProblemRepository problems;
    private final IncidentRepository incidents;
    private final Workflow workflow;
    private final DirectoryLookup directory;
    private final IncidentEvents events;
    private final AuditPublisher audit;
    private final Clock clock;

    public ProblemService(ProblemRepository problems, IncidentRepository incidents, Workflow workflow,
                          DirectoryLookup directory, IncidentEvents events, AuditPublisher audit, Clock clock) {
        this.problems = problems;
        this.incidents = incidents;
        this.workflow = workflow;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
        this.clock = clock;
    }

    private Problem find(CurrentUser me, long id) {
        return problems.findByIdAndCompanyId(id, me.companyId()).orElseThrow(() -> NotFoundException.of("Problem", id));
    }

    private void checkTeam(CurrentUser me, Long teamId) {
        if (teamId != null && directory.teamInCompany(teamId, me.companyId()).isEmpty()) throw new NotFoundException("Team not found.");
    }

    private void link(CurrentUser me, Problem p, List<Long> ids) {
        for (long iid : ids) {
            incidents.findByIdAndCompanyId(iid, me.companyId()).orElseThrow(() -> NotFoundException.of("Incident", iid));
            p.link(iid);
        }
    }

    private ProblemView view(Problem p, boolean detail) {
        List<IncidentRef> refs = null;
        if (detail) {
            var statuses = workflow.statusesById();
            var priorities = workflow.prioritiesById();
            refs = incidents.findAllById(p.getIncidentIds()).stream().sorted(Comparator.comparing(Incident::getCreatedAt))
                    .map(i -> new IncidentRef(i.getId(), i.getTicketNo(), i.getTitle(), statuses.get(i.getStatusId()).getName(),
                            priorities.get(i.getPriorityId()).getName(), i.getCreatedAt())).toList();
        }
        return new ProblemView(p.getId(), p.getProblemNo(), p.getTitle(), p.getDescription(), p.getStatus(), p.getRootCause(),
                p.getWorkaround(), p.isKnownError(), p.getOwnerTeamId(), p.getCreatedAt(), p.getUpdatedAt(), p.getResolvedAt(),
                p.getIncidentIds().size(), refs);
    }

    @Transactional(readOnly = true)
    public PageResponse<ProblemView> list(CurrentUser me, String status, Boolean knownError, String q, int page, int size) {
        me.require(READERS);
        List<String> statuses = status == null || status.isBlank() ? List.of("") : Arrays.asList(status.split(","));
        String like = q == null || q.isBlank() ? null : "%" + q.trim().toLowerCase() + "%";
        var p = problems.search(me.companyId(), status == null || status.isBlank() ? null : status, statuses, knownError, like,
                PageResponse.pageable(page, size, Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"))));
        return PageResponse.of(p, x -> view(x, false));
    }

    @Transactional(readOnly = true)
    public ProblemView get(CurrentUser me, long id) {
        me.require(READERS);
        return view(find(me, id), true);
    }

    @Transactional
    public ProblemView create(CurrentUser me, CreateProblem b) {
        me.require(WRITERS);
        checkTeam(me, b.ownerTeamId());
        long id = problems.nextId();
        Problem p = new Problem(id, me.companyId(), b.title(), b.description(), b.ownerTeamId(), clock.instant());
        if (b.incidentIds() != null) link(me, p, b.incidentIds());
        problems.save(p);
        audit.record("PROBLEM", id, "CREATE", null, p.auditState());
        events.snapshot(p);
        return view(p, true);
    }

    @Transactional
    public ProblemView update(CurrentUser me, long id, UpdateProblem b) {
        me.require(WRITERS);
        Problem p = find(me, id);
        var before = p.auditState();
        if (b.ownerTeamId() != null) {
            checkTeam(me, b.ownerTeamId());
            p.setOwnerTeamId(b.ownerTeamId());
        }
        if (b.title() != null) p.setTitle(b.title());
        if (b.description() != null) p.setDescription(b.description());
        if (b.rootCause() != null) p.setRootCause(b.rootCause());
        if (b.workaround() != null) p.setWorkaround(b.workaround());
        Instant now = clock.instant();
        if (b.status() != null && !b.status().equals(p.getStatus())) {
            if (!FLOW.get(p.getStatus()).contains(b.status())) {
                throw new BusinessRuleException("Transition " + p.getStatus() + " → " + b.status() + " is not allowed.");
            }
            switch (b.status()) {
                case Problem.KNOWN_ERROR -> {
                    if (p.getWorkaround() == null || p.getWorkaround().isBlank()) {
                        throw new BusinessRuleException("A known error needs a documented workaround.");
                    }
                    p.setKnownError(true);
                }
                case Problem.RESOLVED -> {
                    if (p.getRootCause() == null || p.getRootCause().isBlank()) {
                        throw new BusinessRuleException("Record the root cause before resolving.");
                    }
                    p.setResolvedAt(now);
                }
                case Problem.INVESTIGATING -> p.setResolvedAt(null);
                default -> { }
            }
            p.setStatus(b.status());
        }
        p.touch(now);
        audit.record("PROBLEM", id, "UPDATE", before, p.auditState());
        events.snapshot(p);
        return view(p, true);
    }

    @Transactional
    public ProblemView linkIncidents(CurrentUser me, long id, List<Long> incidentIds) {
        me.require(WRITERS);
        Problem p = find(me, id);
        link(me, p, incidentIds);
        p.touch(clock.instant());
        audit.record("PROBLEM", id, "LINK_INCIDENTS", null, Map.of("incidentIds", incidentIds.toString()));
        events.snapshot(p);
        return view(p, true);
    }

    @Transactional
    public void unlink(CurrentUser me, long id, long incidentId) {
        me.require(WRITERS);
        Problem p = find(me, id);
        if (!p.unlink(incidentId)) throw new NotFoundException("Link not found.");
        p.touch(clock.instant());
        audit.record("PROBLEM", id, "UNLINK_INCIDENT", Map.of("incidentId", incidentId), null);
        events.snapshot(p);
    }
}
