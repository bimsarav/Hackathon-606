package com.esmhub.change.service.change;

import com.esmhub.change.service.approval.ApprovalDtos.ApprovalView;
import com.esmhub.change.service.approval.ApprovalService;
import com.esmhub.change.service.approval.ChangePolicy.Step;
import com.esmhub.change.service.change.ChangeDtos.*;
import com.esmhub.change.service.events.ChangeEvents;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirectoryLookup;
import jakarta.persistence.criteria.Predicate;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ChangeService {
    static final Role[] ALL_VIEWERS = {Role.SERVICE_DESK_AGENT, Role.TEAM_LEAD, Role.SERVICE_MANAGER, Role.CHANGE_MANAGER, Role.AUDITOR, Role.ADMIN};
    static final Role[] AUTHORS = {Role.TECHNICIAN, Role.TEAM_LEAD, Role.SERVICE_MANAGER, Role.CHANGE_MANAGER, Role.ADMIN};
    static final Role[] MANAGERS = {Role.CHANGE_MANAGER, Role.SERVICE_MANAGER, Role.ADMIN};
    static final Set<String> PLAN_OPEN = Set.of("DRAFT", "ASSESSMENT");
    static final Set<String> CALENDAR_STATUSES = Set.of("APPROVAL", "SCHEDULED", "IMPLEMENTING");
    static final Map<String, Set<String>> TRANSITIONS = Map.of(
            "DRAFT", Set.of("ASSESSMENT", "CANCELLED"), "ASSESSMENT", Set.of("APPROVAL", "CANCELLED"),
            "APPROVAL", Set.of("CANCELLED"), "SCHEDULED", Set.of("IMPLEMENTING", "CANCELLED"),
            "IMPLEMENTING", Set.of("IMPLEMENTED", "FAILED"), "IMPLEMENTED", Set.of("CLOSED"), "FAILED", Set.of("CLOSED"));

    private final ChangeRepository changes;
    private final ApprovalService approvals;
    private final DirectoryLookup directory;
    private final ChangeEvents events;
    private final AuditPublisher audit;

    public ChangeService(ChangeRepository changes, ApprovalService approvals, DirectoryLookup directory, ChangeEvents events,
                         AuditPublisher audit) {
        this.changes = changes;
        this.approvals = approvals;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
    }

    // ---------- access ----------
    private boolean inOwnerTeam(CurrentUser me, Change c) {
        return c.getOwnerTeamId() != null && (me.inTeam(c.getOwnerTeamId()) || directory.isMember(c.getOwnerTeamId(), me.userId()));
    }

    boolean canEdit(CurrentUser me, Change c) {
        return me.has(MANAGERS) || (me.has(AUTHORS) && (c.getRequesterId() == me.userId() || inOwnerTeam(me, c)));
    }

    boolean canImplement(CurrentUser me, Change c) {
        return me.has(MANAGERS) || (me.has(Role.TECHNICIAN, Role.TEAM_LEAD) && inOwnerTeam(me, c));
    }

    private boolean canView(CurrentUser me, Change c) {
        if (c.getCompanyId() != me.companyId()) return false;
        return c.getRequesterId() == me.userId() || me.has(ALL_VIEWERS) || inOwnerTeam(me, c) || approvals.involves(c.getId(), me);
    }

    private Change get(CurrentUser me, long id) {
        return changes.findById(id).filter(c -> canView(me, c)).orElseThrow(() -> NotFoundException.of("Change", id));
    }

    // ---------- assessment ----------
    static List<String> missingAssessment(Change c) {
        List<String> m = new ArrayList<>();
        if (c.getRiskLevel() == null) m.add("riskLevel");
        if (c.getImpact() == null) m.add("impact");
        if (c.getRollbackPlan() == null || c.getRollbackPlan().isBlank()) m.add("rollbackPlan");
        if (c.getPlannedStart() == null) m.add("plannedStart");
        if (c.getPlannedEnd() == null) m.add("plannedEnd");
        if (c.getOwnerTeamId() == null) m.add("ownerTeamId");
        return m;
    }

    // ---------- views ----------
    private ChangeView view(CurrentUser me, Change c, boolean detail) {
        List<ApprovalView> chain = detail ? approvals.chain(c.getId()).stream()
                .map(a -> new ApprovalView(a.getId(), a.getChangeId(), c.getChangeNo(), c.getTitle(), c.getChangeType(),
                        c.getRiskLevel(), a.getStepOrder(), a.getApproverId(), a.getApproverRole(), a.getDecision(),
                        a.getComments(), a.getCreatedAt(), a.getDecidedAt())).toList() : List.of();
        List<String> missing = missingAssessment(c);
        return new ChangeView(c.getId(), c.getChangeNo(), c.getTitle(), c.getDescription(), c.getChangeType(), c.getStatus(),
                c.getRiskLevel(), c.getImpact(), c.getRequesterId(), directory.name(c.getRequesterId()), c.getOwnerTeamId(),
                c.getPlannedStart(), c.getPlannedEnd(), c.getActualStart(), c.getActualEnd(), c.getRollbackPlan(),
                c.getCreatedAt(), !PLAN_OPEN.contains(c.getStatus()), missing.isEmpty(), missing, chain,
                detail && PLAN_OPEN.contains(c.getStatus()) && canEdit(me, c), detail && canImplement(me, c));
    }

    // ---------- queries ----------
    @Transactional(readOnly = true)
    public PageResponse<ChangeView> list(CurrentUser me, String view, String status, String type, String risk, String q,
                                         int page, int size) {
        boolean mine = "mine".equals(view) || !me.has(ALL_VIEWERS);
        Specification<Change> spec = (root, cq, cb) -> {
            List<Predicate> p = new ArrayList<>();
            p.add(cb.equal(root.get("companyId"), me.companyId()));
            if (mine) {
                Predicate own = cb.equal(root.get("requesterId"), me.userId());
                p.add(me.teamIds().isEmpty() ? own : cb.or(own, root.get("ownerTeamId").in(me.teamIds())));
            }
            if (status != null && !status.isBlank()) p.add(root.get("status").in((Object[]) status.split(",")));
            if (type != null && !type.isBlank()) p.add(root.get("changeType").in((Object[]) type.split(",")));
            if (risk != null && !risk.isBlank()) p.add(root.get("riskLevel").in((Object[]) risk.split(",")));
            if (q != null && !q.isBlank()) {
                String like = "%" + q.trim().toLowerCase() + "%";
                p.add(cb.or(cb.like(cb.lower(root.get("changeNo")), like), cb.like(cb.lower(root.get("title")), like)));
            }
            return cb.and(p.toArray(Predicate[]::new));
        };
        var res = changes.findAll(spec, PageResponse.pageable(page, size, Sort.by(Sort.Direction.DESC, "createdAt", "id")));
        return PageResponse.of(res, c -> view(me, c, false));
    }

    @Transactional(readOnly = true)
    public ChangeView detail(CurrentUser me, long id) { return view(me, get(me, id), true); }

    /** Collision calendar: changes with a planned window in [from, to] that is still ahead of implementation. */
    @Transactional(readOnly = true)
    public List<CalendarEntry> calendar(CurrentUser me, Instant from, Instant to) {
        if (!me.has(ALL_VIEWERS) && !me.has(Role.TECHNICIAN)) throw new ForbiddenException("The change calendar is for staff.");
        Instant f = from != null ? from : Instant.now();
        Instant t = to != null ? to : f.plus(Duration.ofDays(30));
        if (!t.isAfter(f)) throw new BusinessRuleException("'to' must be after 'from'.");
        List<Change> list = changes.window(me.companyId(), CALENDAR_STATUSES, f, t);
        return list.stream().map(c -> new CalendarEntry(c.getId(), c.getChangeNo(), c.getTitle(), c.getChangeType(), c.getStatus(),
                c.getRiskLevel(), c.getOwnerTeamId(), c.getPlannedStart(), c.getPlannedEnd(),
                list.stream().filter(o -> !o.getId().equals(c.getId()) && o.getPlannedStart().isBefore(c.getPlannedEnd())
                        && o.getPlannedEnd().isAfter(c.getPlannedStart())).map(Change::getId).toList())).toList();
    }

    // ---------- commands ----------
    private void validate(ChangeIn in, CurrentUser me) {
        if (in.plannedStart() != null && in.plannedEnd() != null && !in.plannedEnd().isAfter(in.plannedStart())) {
            throw new BusinessRuleException("plannedEnd must be after plannedStart.");
        }
        if (in.ownerTeamId() != null && directory.teamInCompany(in.ownerTeamId(), me.companyId()).isEmpty()) {
            throw new BusinessRuleException("Unknown owner team.");
        }
    }

    @Transactional
    public ChangeView create(CurrentUser me, ChangeIn in) {
        me.require(AUTHORS);
        validate(in, me);
        Instant now = Instant.now();
        Change c = new Change(me.companyId(), me.userId(), now);
        c.applyPlan(in.title().trim(), in.description(), in.changeType(), in.riskLevel(), in.impact(), in.ownerTeamId(),
                in.plannedStart(), in.plannedEnd(), in.rollbackPlan(), now);
        changes.saveAndFlush(c);
        c.assignNumber();
        audit.record("CHANGE", c.getId(), "CREATE", null, snapshot(c));
        events.snapshot(c);
        return view(me, c, true);
    }

    @Transactional
    public ChangeView update(CurrentUser me, long id, ChangeIn in) {
        Change c = get(me, id);
        if (!canEdit(me, c)) throw new ForbiddenException("You cannot edit this change.");
        if (!PLAN_OPEN.contains(c.getStatus())) throw new ConflictException("The plan is locked once the change is submitted for approval.");
        validate(in, me);
        Map<String, Object> before = snapshot(c);
        c.applyPlan(in.title().trim(), in.description(), in.changeType(), in.riskLevel(), in.impact(), in.ownerTeamId(),
                in.plannedStart(), in.plannedEnd(), in.rollbackPlan(), Instant.now());
        audit.record("CHANGE", c.getId(), "UPDATE", before, snapshot(c));
        events.snapshot(c);
        return view(me, c, true);
    }

    @Transactional
    public ChangeView changeStatus(CurrentUser me, long id, String to) {
        Change c = get(me, id);
        if (!TRANSITIONS.getOrDefault(c.getStatus(), Set.of()).contains(to)) {
            throw new BusinessRuleException("Transition " + c.getStatus() + " -> " + to + " is not allowed.");
        }
        switch (to) {
            case "IMPLEMENTING", "IMPLEMENTED", "FAILED" -> {
                if (!canImplement(me, c)) throw new ForbiddenException("Only the owner team or change management can implement this change.");
            }
            case "CLOSED" -> {
                if (!me.has(Role.CHANGE_MANAGER, Role.ADMIN)) throw new ForbiddenException("Only the change manager can close a change.");
            }
            default -> {
                if (!canEdit(me, c)) throw new ForbiddenException("You cannot progress this change.");
            }
        }
        Instant now = Instant.now();
        Map<String, Object> before = snapshot(c);
        String result = to;
        if ("APPROVAL".equals(to)) {
            List<String> missing = missingAssessment(c);
            if (!missing.isEmpty()) throw new BusinessRuleException("Assessment incomplete: " + String.join(", ", missing));
            List<Step> steps = approvals.stepsFor(c);
            if (steps.isEmpty()) {
                result = "SCHEDULED";   // STANDARD changes are pre-approved
            } else {
                c.setStatus("APPROVAL", now);
                approvals.openStep(c, steps.get(0), now);
                result = "APPROVAL";
            }
        } else if ("CANCELLED".equals(to)) {
            approvals.cancelPending(c, me.userId(), now);
        }
        c.setStatus(result, now);
        if ("FAILED".equals(to)) {
            Set<Long> who = new HashSet<>(Set.of(c.getRequesterId()));
            who.addAll(directory.teamLead(c.getOwnerTeamId()));
            who.addAll(directory.activeUserIdsWithRole(c.getCompanyId(), Role.CHANGE_MANAGER.name()));
            events.notify("change.failed", c, who, c.getChangeNo() + " failed", c.getTitle(), "/changes/" + c.getId());
        }
        audit.record("CHANGE", c.getId(), "STATUS_CHANGE", before, snapshot(c));
        events.snapshot(c);
        return view(me, c, true);
    }

    private Map<String, Object> snapshot(Change c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("status", c.getStatus());
        m.put("changeType", c.getChangeType());
        m.put("riskLevel", c.getRiskLevel());
        m.put("impact", c.getImpact());
        m.put("ownerTeamId", c.getOwnerTeamId());
        m.put("plannedStart", c.getPlannedStart());
        m.put("plannedEnd", c.getPlannedEnd());
        return m;
    }
}
