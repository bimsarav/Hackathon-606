package com.esmhub.incident.service.incident;

import static com.esmhub.common.security.Role.ADMIN;
import static com.esmhub.common.security.Role.AUDITOR;
import static com.esmhub.common.security.Role.CHANGE_MANAGER;
import static com.esmhub.common.security.Role.SERVICE_DESK_AGENT;
import static com.esmhub.common.security.Role.SERVICE_MANAGER;
import static com.esmhub.common.security.Role.TEAM_LEAD;
import static com.esmhub.common.security.Role.TECHNICIAN;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.CsvWriter;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.IncidentProperties;
import com.esmhub.incident.service.events.IncidentEvents;
import com.esmhub.incident.service.incident.IncidentDtos.*;
import com.esmhub.incident.service.problem.ProblemRepository;
import com.esmhub.incident.service.reference.AssignmentRule;
import com.esmhub.incident.service.reference.AssignmentRuleRepository;
import com.esmhub.incident.service.reference.Priority;
import com.esmhub.incident.service.reference.TicketStatus;
import com.esmhub.incident.service.reference.Workflow;
import com.esmhub.incident.service.sla.SlaEngine;
import com.esmhub.incident.service.sla.SlaService;
import jakarta.persistence.criteria.Predicate;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Incident lifecycle (FR-3, FR-5, FR-6): visibility, workflow, SLA clocks, assignment, reopen policy (BQ-3, BQ-4). */
@Service
public class IncidentService {
    static final String CREATE_ENDPOINT = "incidents.create";
    static final Role[] DESK = {SERVICE_DESK_AGENT, TEAM_LEAD, SERVICE_MANAGER};
    static final Role[] SEE_ALL = {SERVICE_DESK_AGENT, TEAM_LEAD, SERVICE_MANAGER, AUDITOR, ADMIN, CHANGE_MANAGER};

    /** List filters; {@code view} is one of all, mine, assigned, queue, open, unassigned. */
    public record Filter(String q, String status, Integer priorityId, Long teamId, Long assigneeId, Long requesterId,
                         String view, boolean breached, String sort) {}

    private final IncidentRepository incidents;
    private final IncidentCommentRepository comments;
    private final WorklogRepository worklogs;
    private final IncidentEventRepository timeline;
    private final IdempotencyKeyRepository idempotency;
    private final ProblemRepository problems;
    private final AssignmentRuleRepository rules;
    private final Workflow workflow;
    private final SlaService sla;
    private final DirectoryLookup directory;
    private final IncidentEvents events;
    private final AuditPublisher audit;
    private final IncidentProperties props;
    private final Clock clock;

    public IncidentService(IncidentRepository incidents, IncidentCommentRepository comments, WorklogRepository worklogs,
                           IncidentEventRepository timeline, IdempotencyKeyRepository idempotency, ProblemRepository problems,
                           AssignmentRuleRepository rules, Workflow workflow, SlaService sla, DirectoryLookup directory,
                           IncidentEvents events, AuditPublisher audit, IncidentProperties props, Clock clock) {
        this.incidents = incidents;
        this.comments = comments;
        this.worklogs = worklogs;
        this.timeline = timeline;
        this.idempotency = idempotency;
        this.problems = problems;
        this.rules = rules;
        this.workflow = workflow;
        this.sla = sla;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
        this.props = props;
        this.clock = clock;
    }

    // ---------- visibility and permissions (BQ-3) ----------
    private static boolean inTeam(CurrentUser me, Long teamId) { return me.inTeam(teamId); }

    boolean canView(CurrentUser me, Incident i) {
        if (i.getCompanyId() != me.companyId()) return false;
        if (me.has(SEE_ALL)) return true;
        if (me.has(TECHNICIAN) && (Objects.equals(i.getAssignedUserId(), me.userId()) || inTeam(me, i.getAssignedTeamId()))) {
            return true;
        }
        return i.getRequesterId() == me.userId();
    }

    /** May post internal notes, log work and move the status. */
    boolean canWork(CurrentUser me, Incident i) {
        if (me.has(DESK)) return true;
        return me.has(TECHNICIAN) && (Objects.equals(i.getAssignedUserId(), me.userId()) || inTeam(me, i.getAssignedTeamId()));
    }

    private void requireWork(CurrentUser me, Incident i) {
        if (!canWork(me, i)) throw new ForbiddenException("You are not allowed to work on this incident.");
    }

    Incident visible(CurrentUser me, long id) {
        return incidents.findByIdAndCompanyId(id, me.companyId()).filter(i -> canView(me, i))
                .orElseThrow(() -> NotFoundException.of("Incident", id));
    }

    // ---------- reads ----------
    @Transactional(readOnly = true)
    public IncidentView get(CurrentUser me, long id) { return detail(me, visible(me, id)); }

    @Transactional(readOnly = true)
    public PageResponse<IncidentView> list(CurrentUser me, Filter f, int page, int size) {
        Map<Integer, TicketStatus> statuses = workflow.statusesById();
        Map<Integer, Priority> priorities = workflow.prioritiesById();
        Page<Incident> p = incidents.findAll(spec(me, f, statuses), PageResponse.pageable(page, size, sort(f.sort())));
        return PageResponse.of(p, i -> summary(i, statuses, priorities));
    }

    @Transactional
    public ResponseEntity<byte[]> export(CurrentUser me, Filter f) {
        me.require(SERVICE_DESK_AGENT, TEAM_LEAD, SERVICE_MANAGER, AUDITOR);
        Map<Integer, TicketStatus> statuses = workflow.statusesById();
        Map<Integer, Priority> priorities = workflow.prioritiesById();
        List<Incident> rows = incidents.findAll(spec(me, f, statuses),
                PageRequest.of(0, props.exportMaxRows(), sort("created"))).getContent();
        audit.record("INCIDENT", 0, "EXPORT", null, Map.of("rows", rows.size()));
        List<List<?>> out = rows.stream().<List<?>>map(i -> List.of(i.getTicketNo(), i.getTitle(),
                statuses.get(i.getStatusId()).getName(), priorities.get(i.getPriorityId()).getName(), i.getChannel(),
                nz(directory.name(i.getRequesterId())), nz(teamName(i.getAssignedTeamId())), nz(directory.name(i.getAssignedUserId())),
                nz(i.getCreatedAt()), nz(i.getFirstResponseAt()), nz(i.getResolvedAt()), nz(i.getDueAt()),
                i.isResponseBreached(), i.isResolutionBreached(), i.getReopenedCount())).toList();
        return CsvWriter.response("incidents.csv", List.of("ticket_no", "title", "status", "priority", "channel", "requester",
                "team", "assignee", "created_at", "first_response_at", "resolved_at", "due_at", "response_breached",
                "resolution_breached", "reopened_count"), out);
    }

    private static Object nz(Object o) { return o == null ? "" : o; }

    private static Sort sort(String s) {
        Sort.Order tie = Sort.Order.desc("id");
        return switch (s == null ? "created" : s) {
            case "-created" -> Sort.by(Sort.Order.asc("createdAt"), tie);
            case "due" -> Sort.by(Sort.Order.asc("dueAt").nullsLast(), tie);
            case "priority" -> Sort.by(Sort.Order.asc("priorityId"), tie);
            case "created" -> Sort.by(Sort.Order.desc("createdAt"), tie);
            default -> throw new BusinessRuleException("sort must be one of created, -created, due, priority.");
        };
    }

    /** Row-level visibility mirrors {@link #canView} (NFR-1) plus the user's filters. */
    Specification<Incident> spec(CurrentUser me, Filter f, Map<Integer, TicketStatus> statuses) {
        Set<Integer> closed = statuses.values().stream().filter(TicketStatus::isClosed).map(TicketStatus::getId)
                .collect(Collectors.toSet());
        Set<Integer> named = f.status() == null || f.status().isBlank() ? Set.of()
                : statuses.values().stream().filter(s -> Set.of(f.status().split(",")).contains(s.getName()))
                        .map(TicketStatus::getId).collect(Collectors.toSet());
        String view = f.view() == null ? "all" : f.view();
        if (!Set.of("all", "mine", "assigned", "queue", "open", "unassigned").contains(view)) {
            throw new BusinessRuleException("view must be one of all, mine, assigned, queue, open, unassigned.");
        }
        return (root, query, cb) -> {
            List<Predicate> p = new ArrayList<>();
            p.add(cb.equal(root.get("companyId"), me.companyId()));
            if (!me.has(SEE_ALL)) {
                List<Predicate> any = new ArrayList<>();
                any.add(cb.equal(root.get("requesterId"), me.userId()));
                if (me.has(TECHNICIAN)) {
                    any.add(cb.equal(root.get("assignedUserId"), me.userId()));
                    if (!me.teamIds().isEmpty()) any.add(root.get("assignedTeamId").in(me.teamIds()));
                }
                p.add(cb.or(any.toArray(new Predicate[0])));
            }
            if (f.q() != null && !f.q().isBlank()) {
                String like = "%" + f.q().trim().toLowerCase() + "%";
                p.add(cb.or(cb.like(cb.lower(root.get("ticketNo")), like), cb.like(cb.lower(root.get("title")), like)));
            }
            if (!named.isEmpty()) p.add(root.get("statusId").in(named));
            if (f.priorityId() != null) p.add(cb.equal(root.get("priorityId"), f.priorityId()));
            if (f.teamId() != null) p.add(cb.equal(root.get("assignedTeamId"), f.teamId()));
            if (f.assigneeId() != null) p.add(cb.equal(root.get("assignedUserId"), f.assigneeId()));
            if (f.requesterId() != null) p.add(cb.equal(root.get("requesterId"), f.requesterId()));
            Predicate notClosed = cb.not(root.get("statusId").in(closed));
            switch (view) {
                case "mine" -> p.add(cb.equal(root.get("requesterId"), me.userId()));
                case "assigned" -> { p.add(cb.equal(root.get("assignedUserId"), me.userId())); p.add(notClosed); }
                case "queue" -> {
                    p.add(me.teamIds().isEmpty() ? cb.disjunction() : root.get("assignedTeamId").in(me.teamIds()));
                    p.add(notClosed);
                }
                case "open" -> p.add(notClosed);
                case "unassigned" -> { p.add(cb.isNull(root.get("assignedUserId"))); p.add(notClosed); }
                default -> { }
            }
            if (f.breached()) p.add(cb.or(cb.isTrue(root.get("responseBreached")), cb.isTrue(root.get("resolutionBreached"))));
            return cb.and(p.toArray(new Predicate[0]));
        };
    }

    private String teamName(Long teamId) { return directory.team(teamId).map(t -> t.getName()).orElse(null); }

    private IncidentView summary(Incident i, Map<Integer, TicketStatus> statuses, Map<Integer, Priority> priorities) {
        return new IncidentView(i.getId(), i.getTicketNo(), i.getTitle(), statuses.get(i.getStatusId()).getName(),
                priorities.get(i.getPriorityId()).getName(), i.getPriorityId(), i.getChannel(), i.getServiceId(), i.getAssetId(),
                i.getRequesterId(), directory.name(i.getRequesterId()), i.getAssignedTeamId(), teamName(i.getAssignedTeamId()),
                i.getAssignedUserId(), directory.name(i.getAssignedUserId()), i.getCreatedAt(), i.getUpdatedAt(),
                i.getFirstResponseAt(), i.getResolvedAt(), i.getClosedAt(), i.getResponseDueAt(), i.getDueAt(),
                i.getSlaPausedSince() != null, i.isResponseBreached(), i.isResolutionBreached(), i.getReopenedCount(),
                i.getSatisfactionScore(), null, null, null, null, null, null, null, null, null, null);
    }

    private IncidentView detail(CurrentUser me, Incident i) {
        IncidentView s = summary(i, Map.of(i.getStatusId(), workflow.status(i.getStatusId())),
                Map.of(i.getPriorityId(), workflow.prioritiesById().get(i.getPriorityId())));
        boolean staff = me.isStaff() || me.has(AUDITOR, ADMIN);
        List<CommentView> cs = comments.findByIncidentIdOrderByCreatedAtAscIdAsc(i.getId()).stream()
                .filter(c -> staff || !c.isInternal())
                .map(c -> new CommentView(c.getId(), c.getAuthorId(), directory.name(c.getAuthorId()), c.getBody(),
                        c.isInternal(), c.getCreatedAt())).toList();
        List<WorklogView> ws = !staff ? List.of() : worklogs.findByIncidentIdOrderByLoggedAtAscIdAsc(i.getId()).stream()
                .map(w -> new WorklogView(w.getId(), w.getUserId(), directory.name(w.getUserId()), w.getMinutesSpent(),
                        w.getWorkDescription(), w.getLoggedAt())).toList();
        List<EventView> es = timeline.findByIncidentIdOrderByOccurredAtAscIdAsc(i.getId()).stream()
                .map(e -> new EventView(e.getEventType(), e.getFromValue(), e.getToValue(), e.getActorId(), e.getOccurredAt())).toList();
        List<ProblemRef> ps = problems.findLinkedTo(i.getId()).stream().map(p -> new ProblemRef(p.getId(), p.getProblemNo(),
                p.getTitle(), p.getStatus(), p.isKnownError(), p.getWorkaround())).toList();
        return new IncidentView(s.id(), s.ticketNo(), s.title(), s.status(), s.priority(), s.priorityId(), s.channel(),
                s.serviceId(), s.assetId(), s.requesterId(), s.requesterName(), s.assignedTeamId(), s.teamName(),
                s.assignedUserId(), s.assigneeName(), s.createdAt(), s.updatedAt(), s.firstResponseAt(), s.resolvedAt(),
                s.closedAt(), s.responseDueAt(), s.dueAt(), s.slaPaused(), s.responseBreached(), s.resolutionBreached(),
                s.reopenedCount(), s.satisfactionScore(), i.getDescription(), i.getResolutionCode(), i.getResolutionNotes(),
                i.getSlaPausedMinutes(), cs, ws, es, ps, workflow.allowedFrom(i.getStatusId()), canWork(me, i));
    }

    // ---------- lifecycle ----------
    /** Assignment rules (FR-6): first matching active rule by sort order; fallback is the service's owning team. */
    Long routeTeam(long companyId, Long serviceId, int priorityId) {
        for (AssignmentRule r : rules.findByCompanyIdOrderBySortOrderAscIdAsc(companyId)) {
            if (r.matches(serviceId, priorityId)) return r.getTeamId();
        }
        return directory.service(serviceId).map(s -> s.getOwningTeamId()).orElse(null);
    }

    private void record(Incident i, String type, Long actor, Object from, Object to) {
        timeline.save(new IncidentEvent(i.getId(), type, actor, from, to, clock.instant()));
    }

    @Transactional
    public IncidentView create(CurrentUser me, CreateIncident b, String idempotencyKey) {
        var key = idempotencyKey == null || idempotencyKey.isBlank() ? null
                : new IdempotencyKey.Key(me.userId(), idempotencyKey.substring(0, Math.min(100, idempotencyKey.length())), CREATE_ENDPOINT);
        if (key != null) {
            var existing = idempotency.findById(key);
            if (existing.isPresent()) return detail(me, visible(me, existing.get().getResourceId()));
        }
        long requesterId = me.userId();
        if (b.requesterId() != null && b.requesterId() != me.userId()) {
            if (!me.has(DESK)) throw new ForbiddenException("Only service desk staff can log incidents on behalf of another user.");
            requesterId = directory.userInCompany(b.requesterId(), me.companyId())
                    .orElseThrow(() -> new NotFoundException("Requester not found.")).getUserId();
        }
        if (b.serviceId() != null && directory.serviceInCompany(b.serviceId(), me.companyId()).filter(s -> s.isActive()).isEmpty()) {
            throw new NotFoundException("Service not found.");
        }
        int priorityId = b.priorityId() == null ? 3 : b.priorityId();
        if (priorityId != 3 && !me.has(DESK)) priorityId = 3; // employees cannot self-prioritise; the desk triages (BQ-3)
        if (!workflow.prioritiesById().containsKey(priorityId)) throw new NotFoundException("Priority not found.");
        Instant now = clock.instant();
        Long teamId = routeTeam(me.companyId(), b.serviceId(), priorityId);
        long id = incidents.nextId();
        Incident inc = new Incident(id, me.companyId(), b.title(), b.description(), requesterId, b.serviceId(), b.assetId(),
                priorityId, workflow.status(TicketStatus.NEW).getId(), teamId, b.channel() == null ? "PORTAL" : b.channel(), now);
        sla.apply(inc);
        incidents.save(inc);
        record(inc, "CREATED", me.userId(), null, inc.getTicketNo());
        audit.record("INCIDENT", id, "CREATE", null, inc.auditState());
        events.domain("incident.created", inc, Set.of(requesterId), inc.getTicketNo() + " logged: " + inc.getTitle(),
                "Your incident has been logged.", true, Map.of("channel", inc.getChannel(), "audience", "requester"));
        Set<Long> leads = directory.teamLead(teamId);
        if (!leads.isEmpty()) {
            events.domain("incident.created", inc, leads, "New " + inc.getTicketNo() + " for your team", inc.getTitle(), false,
                    Map.of("channel", inc.getChannel(), "audience", "queue"));
        }
        events.snapshot(inc);
        if (key != null) idempotency.save(new IdempotencyKey(key, id, now));
        return detail(me, inc);
    }

    @Transactional
    public IncidentView update(CurrentUser me, long id, UpdateIncident b) {
        Incident inc = visible(me, id);
        var before = inc.auditState();
        if (workflow.status(inc.getStatusId()).isClosed()) {
            throw new BusinessRuleException("Closed or resolved incidents cannot be edited; reopen first.");
        }
        Instant now = clock.instant();
        if (b.priorityId() != null && b.priorityId() != inc.getPriorityId()) {
            me.require(SERVICE_DESK_AGENT, TEAM_LEAD, SERVICE_MANAGER);
            Priority np = workflow.prioritiesById().get(b.priorityId());
            if (np == null) throw new NotFoundException("Priority not found.");
            record(inc, "PRIORITY_CHANGE", me.userId(), workflow.prioritiesById().get(inc.getPriorityId()).getName(), np.getName());
            inc.setPriorityId(b.priorityId());
            sla.apply(inc);
        }
        if (b.requesterId() != null && b.requesterId() != inc.getRequesterId()) {
            me.require(SERVICE_DESK_AGENT);
            inc.setRequesterId(directory.userInCompany(b.requesterId(), me.companyId())
                    .orElseThrow(() -> new NotFoundException("Requester not found.")).getUserId());
            sla.recompute(inc);
        }
        if (b.serviceId() != null && !b.serviceId().equals(inc.getServiceId())) {
            requireWork(me, inc);
            if (directory.serviceInCompany(b.serviceId(), me.companyId()).isEmpty()) throw new NotFoundException("Service not found.");
            inc.setServiceId(b.serviceId());
            sla.apply(inc);
        }
        if (b.title() != null || b.assetId() != null) {
            if (inc.getRequesterId() != me.userId()) requireWork(me, inc);
            if (b.title() != null) inc.setTitle(b.title());
            if (b.assetId() != null) inc.setAssetId(b.assetId());
        }
        inc.touch(now);
        audit.record("INCIDENT", id, "UPDATE", before, inc.auditState());
        events.snapshot(inc);
        return detail(me, inc);
    }

    @Transactional
    public IncidentView assign(CurrentUser me, long id, Assign b) {
        Incident inc = visible(me, id);
        if (workflow.status(inc.getStatusId()).isClosed()) throw new BusinessRuleException("Cannot assign a closed or resolved incident.");
        boolean selfAssign = b.userId() != null && b.userId() == me.userId() && me.has(TECHNICIAN);
        if (!(me.has(SERVICE_DESK_AGENT, TEAM_LEAD) || selfAssign)) {
            throw new ForbiddenException("Only service desk agents and team leads can assign incidents.");
        }
        Long teamId = b.teamId() != null ? b.teamId() : inc.getAssignedTeamId();
        if (teamId != null && directory.teamInCompany(teamId, me.companyId()).filter(t -> t.isActive()).isEmpty()) {
            throw new NotFoundException("Team not found.");
        }
        if (b.userId() != null) {
            DirUser u = directory.userInCompany(b.userId(), me.companyId()).orElseThrow(() -> new NotFoundException("Assignee not found."));
            if (!directory.isMember(teamId, b.userId())) throw new BusinessRuleException("The assignee must be a member of the assigned team.");
            Set<String> staff = Role.STAFF.stream().map(Enum::name).collect(Collectors.toSet());
            if (u.getRoles().stream().noneMatch(staff::contains)) throw new BusinessRuleException("The assignee must hold a resolver role.");
        }
        var before = inc.auditState();
        Long previous = inc.getAssignedUserId();
        inc.assignTo(teamId, b.userId());
        if (TicketStatus.NEW.equals(workflow.status(inc.getStatusId()).getName()) && b.userId() != null) {
            moveStatus(inc, TicketStatus.ASSIGNED, me.userId(), clock.instant());
        }
        inc.touch(clock.instant());
        record(inc, "ASSIGN", me.userId(), previous, b.userId());
        audit.record("INCIDENT", id, "ASSIGN", before, inc.auditState());
        Set<Long> to = b.userId() != null && b.userId() != me.userId() ? Set.of(b.userId()) : Set.of();
        events.domain("incident.assigned", inc, to, inc.getTicketNo() + " assigned to you", inc.getTitle(), true,
                Map.of("assignedUserId", nzl(b.userId()), "assignedTeamId", nzl(teamId)));
        events.snapshot(inc);
        return detail(me, inc);
    }

    private static Object nzl(Long v) { return v == null ? "" : v; }

    /** Moves the status after the workflow check, keeping the SLA pause clock and the timestamps consistent. */
    void moveStatus(Incident inc, String toName, Long actor, Instant ts) {
        TicketStatus to = workflow.status(toName);
        TicketStatus from = workflow.status(inc.getStatusId());
        if (from.getId().equals(to.getId())) return;
        workflow.check(from, to);
        SlaEngine.Calendar cal = sla.calendarForUser(inc.getRequesterId());
        SlaEngine.Targets targets = sla.targetsFor(inc);
        if (from.isPausesSla() && inc.getSlaPausedSince() != null) {
            inc.addPausedMinutes(SlaEngine.businessMinutesBetween(inc.getSlaPausedSince(), ts, cal, targets.businessHours()));
            inc.setSlaPausedSince(null);
            sla.recompute(inc);
            record(inc, "SLA_RESUME", actor, null, inc.getSlaPausedMinutes());
        }
        if (to.isPausesSla()) {
            inc.setSlaPausedSince(ts);
            record(inc, "SLA_PAUSE", actor, null, null);
        }
        if (TicketStatus.IN_PROGRESS.equals(to.getName()) && inc.getFirstResponseAt() == null) inc.setFirstResponseAt(ts);
        if (TicketStatus.RESOLVED.equals(to.getName())) {
            inc.setResolvedAt(ts);
            inc.setResolutionBreached(inc.getDueAt() != null && ts.isAfter(inc.getDueAt()));
        }
        if (TicketStatus.CLOSED.equals(to.getName()) || TicketStatus.CANCELLED.equals(to.getName())) inc.setClosedAt(ts);
        record(inc, "STATUS_CHANGE", actor, from.getName(), to.getName());
        inc.setStatusId(to.getId());
    }

    @Transactional
    public IncidentView changeStatus(CurrentUser me, long id, ChangeStatus b) {
        Incident inc = visible(me, id);
        var before = inc.auditState();
        String to = b.status();
        if (TicketStatus.CANCELLED.equals(to)) {
            if (!(inc.getRequesterId() == me.userId() || me.has(SERVICE_DESK_AGENT, TEAM_LEAD))) {
                throw new ForbiddenException("Only the requester or the service desk can cancel.");
            }
        } else if (TicketStatus.CLOSED.equals(to)) {
            if (!(inc.getRequesterId() == me.userId() || canWork(me, inc))) throw new ForbiddenException("Not allowed to close this incident.");
        } else {
            requireWork(me, inc);
        }
        if (TicketStatus.RESOLVED.equals(to)) {
            if (b.resolutionCode() == null || b.resolutionCode().isBlank()) throw new BusinessRuleException("A resolution code is required to resolve.");
            if (!(Objects.equals(inc.getAssignedUserId(), me.userId()) || me.has(TEAM_LEAD, SERVICE_DESK_AGENT, SERVICE_MANAGER))) {
                throw new ForbiddenException("Only the assignee or a team lead can resolve.");
            }
            inc.setResolution(b.resolutionCode(), b.resolutionNotes());
        }
        moveStatus(inc, to, me.userId(), clock.instant());
        inc.touch(clock.instant());
        audit.record("INCIDENT", id, TicketStatus.CLOSED.equals(to) || TicketStatus.CANCELLED.equals(to) ? "CLOSE" : "STATUS_CHANGE",
                before, inc.auditState());
        boolean notify = TicketStatus.RESOLVED.equals(to) || TicketStatus.PENDING_USER.equals(to);
        events.domain("incident.status_changed", inc, notify ? Set.of(inc.getRequesterId()) : Set.of(),
                inc.getTicketNo() + " is " + to.replace('_', ' ').toLowerCase(), inc.getTitle(), notify, Map.of("to", to));
        events.snapshot(inc);
        return detail(me, inc);
    }

    /** BQ-4: only RESOLVED incidents, within the reopen window, by the requester or service desk staff. */
    @Transactional
    public IncidentView reopen(CurrentUser me, long id, Reopen b) {
        Incident inc = visible(me, id);
        if (!TicketStatus.RESOLVED.equals(workflow.status(inc.getStatusId()).getName())) {
            throw new BusinessRuleException("Only resolved incidents can be reopened (closed incidents need a new ticket).");
        }
        if (!(inc.getRequesterId() == me.userId() || me.has(SERVICE_DESK_AGENT, TEAM_LEAD))) {
            throw new ForbiddenException("Only the requester or the service desk can reopen.");
        }
        Instant now = clock.instant();
        Duration window = Duration.ofDays(props.reopenWindowDays());
        if (inc.getResolvedAt() != null && Duration.between(inc.getResolvedAt(), now).compareTo(window) > 0) {
            throw new BusinessRuleException("The reopen window of " + window.toDays() + " days has passed.");
        }
        var before = inc.auditState();
        moveStatus(inc, TicketStatus.IN_PROGRESS, me.userId(), now);
        inc.setResolvedAt(null);
        inc.setResolution(null, inc.getResolutionNotes());
        inc.setResolutionBreached(false);
        inc.incrementReopened();
        inc.touch(now);
        record(inc, "REOPEN", me.userId(), null, b.reason());
        audit.record("INCIDENT", id, "REOPEN", before, inc.auditState());
        Set<Long> to = new HashSet<>(directory.teamLead(inc.getAssignedTeamId()));
        if (inc.getAssignedUserId() != null) to.add(inc.getAssignedUserId());
        events.domain("incident.reopened", inc, to, inc.getTicketNo() + " reopened", b.reason(), true,
                Map.of("reopenedCount", inc.getReopenedCount()));
        events.snapshot(inc);
        return detail(me, inc);
    }

    @Transactional
    public CommentView comment(CurrentUser me, long id, AddComment b) {
        Incident inc = visible(me, id);
        boolean requester = inc.getRequesterId() == me.userId();
        boolean worker = canWork(me, inc);
        if (b.isInternal() && !worker) throw new ForbiddenException("Only resolvers can add internal notes.");
        if (!(requester || worker)) throw new ForbiddenException("You cannot comment on this incident.");
        String status = workflow.status(inc.getStatusId()).getName();
        if (TicketStatus.CLOSED.equals(status) || TicketStatus.CANCELLED.equals(status)) {
            throw new BusinessRuleException("Closed incidents cannot be commented on.");
        }
        Instant now = clock.instant();
        IncidentComment c = comments.save(new IncidentComment(id, me.userId(), b.body(), b.isInternal(), now));
        Set<Long> to = Set.of();
        boolean email = false;
        String subject = "Update on " + inc.getTicketNo();
        if (worker && !b.isInternal() && !requester) {
            if (inc.getFirstResponseAt() == null) inc.setFirstResponseAt(now);
            to = Set.of(inc.getRequesterId());
            email = true;
        } else if (requester && inc.getAssignedUserId() != null) {
            to = Set.of(inc.getAssignedUserId());
            subject = "Requester replied on " + inc.getTicketNo();
        }
        inc.touch(now);
        audit.record("INCIDENT", id, "COMMENT", null, Map.of("commentId", c.getId(), "internal", c.isInternal()));
        events.domain("incident.commented", inc, to, subject, b.isInternal() ? "" : abbreviate(b.body()), email,
                Map.of("internal", b.isInternal()));
        events.snapshot(inc);
        return new CommentView(c.getId(), c.getAuthorId(), me.name(), c.getBody(), c.isInternal(), c.getCreatedAt());
    }

    private static String abbreviate(String s) { return s.length() > 500 ? s.substring(0, 500) : s; }

    @Transactional
    public WorklogView worklog(CurrentUser me, long id, AddWorklog b) {
        Incident inc = visible(me, id);
        requireWork(me, inc);
        Worklog w = worklogs.save(new Worklog(id, me.userId(), b.minutesSpent(), b.workDescription(), clock.instant()));
        audit.record("INCIDENT", id, "WORKLOG", null, Map.of("worklogId", w.getId(), "minutes", w.getMinutesSpent()));
        events.snapshot(inc);
        return new WorklogView(w.getId(), w.getUserId(), me.name(), w.getMinutesSpent(), w.getWorkDescription(), w.getLoggedAt());
    }

    @Transactional
    public IncidentView rate(CurrentUser me, long id, int score) {
        Incident inc = visible(me, id);
        if (inc.getRequesterId() != me.userId()) throw new ForbiddenException("Only the requester can rate an incident.");
        String st = workflow.status(inc.getStatusId()).getName();
        if (!(TicketStatus.RESOLVED.equals(st) || TicketStatus.CLOSED.equals(st))) {
            throw new BusinessRuleException("Only resolved or closed incidents can be rated.");
        }
        inc.setSatisfactionScore(score);
        audit.record("INCIDENT", id, "RATE", null, Map.of("satisfactionScore", score));
        events.snapshot(inc);
        return detail(me, inc);
    }

    public List<Priority> priorities() { return workflow.prioritiesById().values().stream().sorted(java.util.Comparator.comparing(Priority::getId)).toList(); }

}
