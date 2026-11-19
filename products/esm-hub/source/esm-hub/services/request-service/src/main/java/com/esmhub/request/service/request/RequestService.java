package com.esmhub.request.service.request;

import com.esmhub.request.service.approval.ApprovalDtos.ApprovalView;
import com.esmhub.request.service.approval.ApprovalEngine.StepSpec;
import com.esmhub.request.service.approval.ApprovalService;
import com.esmhub.request.service.catalogue.CatalogueItem;
import com.esmhub.request.service.catalogue.CatalogueItemRepository;
import com.esmhub.request.service.events.RequestEvents;
import com.esmhub.request.service.request.RequestDtos.*;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirectoryLookup;
import jakarta.persistence.criteria.Predicate;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RequestService {
    static final String SCOPE = "requests.create";
    static final Role[] ALL_VIEWERS = {Role.SERVICE_DESK_AGENT, Role.TEAM_LEAD, Role.SERVICE_MANAGER, Role.AUDITOR, Role.ADMIN};
    static final Map<String, Set<String>> TRANSITIONS = Map.of(
            "APPROVED", Set.of("IN_PROGRESS", "CANCELLED"), "IN_PROGRESS", Set.of("FULFILLED"),
            "SUBMITTED", Set.of("CANCELLED"), "PENDING_APPROVAL", Set.of("CANCELLED"));

    private final ServiceRequestRepository requests;
    private final CatalogueItemRepository items;
    private final IdempotencyKeyRepository idem;
    private final ApprovalService approvals;
    private final DirectoryLookup directory;
    private final RequestEvents events;
    private final AuditPublisher audit;

    public RequestService(ServiceRequestRepository requests, CatalogueItemRepository items, IdempotencyKeyRepository idem,
                          ApprovalService approvals, DirectoryLookup directory, RequestEvents events, AuditPublisher audit) {
        this.requests = requests;
        this.items = items;
        this.idem = idem;
        this.approvals = approvals;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
    }

    // ---------- access ----------
    boolean canFulfil(CurrentUser me, ServiceRequest r) {
        if (me.has(Role.SERVICE_DESK_AGENT, Role.TEAM_LEAD, Role.SERVICE_MANAGER)) return true;
        return me.has(Role.TECHNICIAN) && r.getAssignedTeamId() != null
                && (me.inTeam(r.getAssignedTeamId()) || directory.isMember(r.getAssignedTeamId(), me.userId()));
    }

    private boolean canView(CurrentUser me, ServiceRequest r) {
        if (r.getCompanyId() != me.companyId()) return false;
        return r.getRequesterId() == me.userId() || me.has(ALL_VIEWERS) || canFulfil(me, r) || approvals.involves(r.getId(), me);
    }

    private ServiceRequest get(CurrentUser me, long id) {
        return requests.findById(id).filter(r -> canView(me, r)).orElseThrow(() -> NotFoundException.of("Service request", id));
    }

    // ---------- views ----------
    private RequestView view(CurrentUser me, ServiceRequest r, boolean detail) {
        List<ApprovalView> chain = detail ? approvals.chain(r.getId()).stream()
                .map(a -> new ApprovalView(a.getId(), a.getRequestId(), r.getRequestNo(), r.getTitle(), a.getStepOrder(),
                        a.getApproverId(), a.getApproverRole(), a.getDecision(), a.getComments(), a.getCreatedAt(),
                        a.getDecidedAt())).toList() : List.of();
        return new RequestView(r.getId(), r.getRequestNo(), r.getTitle(), r.getDetails(), r.getStatus(), r.getRequesterId(),
                directory.name(r.getRequesterId()), r.getServiceId(), r.getItemId(), r.getEstimatedCost(),
                r.getAssignedTeamId(), r.getAssignedUserId(), r.getRequestedAt(), r.getApprovedAt(), r.getFulfilledAt(),
                chain, detail && canFulfil(me, r));
    }

    // ---------- queries ----------
    @Transactional(readOnly = true)
    public PageResponse<RequestView> list(CurrentUser me, String view, String status, String q, int page, int size) {
        boolean wide = me.has(ALL_VIEWERS) || me.has(Role.TECHNICIAN);
        boolean mine = "mine".equals(view) || !wide;
        boolean fulfilment = !mine && ("fulfilment".equals(view) || (me.has(Role.TECHNICIAN) && !me.has(ALL_VIEWERS)));
        Specification<ServiceRequest> spec = (root, cq, cb) -> {
            List<Predicate> p = new ArrayList<>();
            p.add(cb.equal(root.get("companyId"), me.companyId()));
            if (mine) p.add(cb.equal(root.get("requesterId"), me.userId()));
            else if (fulfilment) {
                p.add(me.teamIds().isEmpty() ? cb.disjunction() : root.get("assignedTeamId").in(me.teamIds()));
            }
            if (status != null && !status.isBlank()) p.add(root.get("status").in((Object[]) status.split(",")));
            if (q != null && !q.isBlank()) {
                String like = "%" + q.trim().toLowerCase() + "%";
                p.add(cb.or(cb.like(cb.lower(root.get("requestNo")), like), cb.like(cb.lower(root.get("title")), like)));
            }
            return cb.and(p.toArray(Predicate[]::new));
        };
        var res = requests.findAll(spec, PageResponse.pageable(page, size, Sort.by(Sort.Direction.DESC, "requestedAt", "id")));
        return PageResponse.of(res, r -> view(me, r, false));
    }

    @Transactional(readOnly = true)
    public RequestView detail(CurrentUser me, long id) { return view(me, get(me, id), true); }

    // ---------- commands ----------
    @Transactional
    public RequestView create(CurrentUser me, CreateRequest req, String idempotencyKey) {
        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            var existing = idem.findById(new IdempotencyKey.Pk(me.userId(), idempotencyKey, SCOPE));
            if (existing.isPresent()) return view(me, get(me, existing.get().getEntityId()), true);
        }
        CatalogueItem item = items.findById(req.itemId()).filter(i -> i.getCompanyId() == me.companyId())
                .orElseThrow(() -> NotFoundException.of("Catalogue item", req.itemId()));
        if (!item.isActive()) throw new BusinessRuleException("This catalogue item is not available.");
        BigDecimal cost = req.estimatedCost() != null ? req.estimatedCost() : item.getBaseCost();
        Instant now = Instant.now();
        ServiceRequest r = new ServiceRequest(me.companyId(), me.userId(), item.getServiceId(), item.getId(),
                req.title() == null || req.title().isBlank() ? item.getName() : req.title().trim(), req.details(), cost,
                item.getFulfilmentTeamId(), now);
        requests.saveAndFlush(r);
        r.assignNumber();
        List<StepSpec> steps = approvals.stepsFor(r);
        if (steps.isEmpty()) {
            r.setStatus("APPROVED", now);
        } else {
            r.setStatus("PENDING_APPROVAL", now);
            approvals.openStep(r, steps.get(0), now);
        }
        events.notify("request.submitted", r, directory.teamLead(r.getAssignedTeamId()), r.getRequestNo() + " submitted",
                r.getTitle(), "/requests/" + r.getId());
        audit.record("SERVICE_REQUEST", r.getId(), "CREATE", null, snapshot(r));
        events.snapshot(r);
        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            idem.save(new IdempotencyKey(me.userId(), idempotencyKey, SCOPE, r.getId()));
        }
        return view(me, r, true);
    }

    @Transactional
    public RequestView changeStatus(CurrentUser me, long id, String to) {
        ServiceRequest r = get(me, id);
        if (!TRANSITIONS.getOrDefault(r.getStatus(), Set.of()).contains(to)) {
            throw new BusinessRuleException("Transition " + r.getStatus() + " -> " + to + " is not allowed.");
        }
        Instant now = Instant.now();
        if ("CANCELLED".equals(to)) {
            if (!(r.getRequesterId() == me.userId() || me.has(Role.SERVICE_DESK_AGENT, Role.SERVICE_MANAGER))) {
                throw new ForbiddenException("Only the requester or the service desk can cancel.");
            }
            approvals.cancelPending(r, me.userId(), now);
        } else if (!canFulfil(me, r)) {
            throw new ForbiddenException("Only the fulfilment team can progress this request.");
        }
        Map<String, Object> before = snapshot(r);
        r.setStatus(to, now);
        if ("IN_PROGRESS".equals(to) && r.getAssignedUserId() == null) r.assignTo(me.userId());
        if ("FULFILLED".equals(to)) {
            events.notify("request.fulfilled", r, Set.of(r.getRequesterId()), r.getRequestNo() + " fulfilled", r.getTitle(),
                    "/requests/" + r.getId());
        }
        audit.record("SERVICE_REQUEST", r.getId(), "STATUS_CHANGE", before, snapshot(r));
        events.snapshot(r);
        return view(me, r, true);
    }

    private Map<String, Object> snapshot(ServiceRequest r) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("status", r.getStatus());
        m.put("assignedTeamId", r.getAssignedTeamId());
        m.put("assignedUserId", r.getAssignedUserId());
        m.put("estimatedCost", r.getEstimatedCost());
        m.put("fulfilledAt", r.getFulfilledAt());
        return m;
    }
}
