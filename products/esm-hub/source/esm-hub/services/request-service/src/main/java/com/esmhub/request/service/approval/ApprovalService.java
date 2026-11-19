package com.esmhub.request.service.approval;

import com.esmhub.request.service.approval.ApprovalDtos.ApprovalView;
import com.esmhub.request.service.approval.ApprovalEngine.Approver;
import com.esmhub.request.service.approval.ApprovalEngine.StepSpec;
import com.esmhub.request.service.catalogue.CatalogueItem;
import com.esmhub.request.service.catalogue.CatalogueItemRepository;
import com.esmhub.request.service.events.RequestEvents;
import com.esmhub.request.service.request.ServiceRequest;
import com.esmhub.request.service.request.ServiceRequestRepository;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Opens approval steps and records decisions (FR-4). Rules live in {@link ApprovalEngine}. */
@Service
public class ApprovalService {
    private final RequestApprovalRepository approvals;
    private final ServiceRequestRepository requests;
    private final CatalogueItemRepository items;
    private final DirectoryLookup directory;
    private final RequestEvents events;
    private final AuditPublisher audit;

    public ApprovalService(RequestApprovalRepository approvals, ServiceRequestRepository requests,
                           CatalogueItemRepository items, DirectoryLookup directory, RequestEvents events,
                           AuditPublisher audit) {
        this.approvals = approvals;
        this.requests = requests;
        this.items = items;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
    }

    public List<StepSpec> stepsFor(ServiceRequest r) {
        if (r.getItemId() == null) return List.of();
        return items.findById(r.getItemId()).map(i -> ApprovalEngine.applicableSteps(i.getSteps(), r.getEstimatedCost()))
                .orElse(List.of());
    }

    /** Creates the pending approval for a step and notifies the approvers (never the requester). */
    public RequestApproval openStep(ServiceRequest r, StepSpec step, Instant now) {
        Long managerId = directory.userInCompany(r.getRequesterId(), r.getCompanyId()).map(DirUser::getManagerId)
                .flatMap(m -> directory.userInCompany(m, r.getCompanyId())).map(DirUser::getUserId).orElse(null);
        Approver ap = ApprovalEngine.resolve(step, managerId);
        RequestApproval a = approvals.save(new RequestApproval(r.getId(), step.order(), ap.userId(), ap.role(), now));
        Set<Long> recipients = ap.userId() != null ? new HashSet<>(Set.of(ap.userId()))
                : new HashSet<>(directory.activeUserIdsWithRole(r.getCompanyId(), ap.role()));
        recipients.remove(r.getRequesterId());
        events.notify("request.approval_requested", r, recipients, "Approval needed: " + r.getRequestNo(), r.getTitle(), "/approvals");
        return a;
    }

    @Transactional(readOnly = true)
    public List<ApprovalView> pending(CurrentUser me) {
        Set<String> roles = me.roles().isEmpty() ? Set.of("-") : me.roles();
        return approvals.pendingFor(me.companyId(), me.userId(), roles).stream().map(a -> Map.entry(a, requests.findById(a.getRequestId())))
                .filter(e -> e.getValue().isPresent())
                .filter(e -> ApprovalEngine.canDecide(e.getKey(), e.getValue().get().getRequesterId(), me))
                .map(e -> view(e.getKey(), e.getValue().get())).toList();
    }

    @Transactional
    public ApprovalView decide(CurrentUser me, long approvalId, String decision, String comments) {
        RequestApproval a = approvals.lockById(approvalId).orElseThrow(() -> NotFoundException.of("Approval", approvalId));
        ServiceRequest r = requests.findById(a.getRequestId()).filter(x -> x.getCompanyId() == me.companyId())
                .orElseThrow(() -> NotFoundException.of("Approval", approvalId));
        if (!a.isPending()) throw new ConflictException("This approval has already been decided.");
        if (!ApprovalEngine.canDecide(a, r.getRequesterId(), me)) throw new ForbiddenException("You are not an approver for this step.");
        Instant now = Instant.now();
        a.decide(decision, comments, me.userId(), now);
        audit.record("SERVICE_REQUEST", r.getId(), "APPROVAL_" + decision, null,
                Map.of("approvalId", a.getId(), "step", a.getStepOrder()));
        String link = "/requests/" + r.getId();
        if ("REJECTED".equals(decision)) {
            r.setStatus("REJECTED", now);
            events.notify("request.rejected", r, Set.of(r.getRequesterId()), r.getRequestNo() + " was rejected",
                    comments == null ? "" : comments, link);
        } else {
            Optional<StepSpec> next = ApprovalEngine.nextAfter(stepsFor(r), a.getStepOrder());
            if (next.isPresent()) {
                openStep(r, next.get(), now);
            } else {
                r.setStatus("APPROVED", now);
                events.notify("request.approved", r, Set.of(r.getRequesterId()), r.getRequestNo() + " approved", r.getTitle(), link);
            }
        }
        requests.save(r);
        events.snapshot(r);
        return view(a, r);
    }

    /** Cancelling a request closes its open approvals. */
    public void cancelPending(ServiceRequest r, long by, Instant now) {
        for (RequestApproval a : approvals.findByRequestIdAndDecision(r.getId(), "PENDING")) {
            a.decide("REJECTED", "Request cancelled", by, now);
        }
    }

    public List<RequestApproval> chain(long requestId) { return approvals.findByRequestIdOrderByStepOrderAscIdAsc(requestId); }

    public boolean involves(long requestId, CurrentUser me) {
        return approvals.involves(requestId, me.userId(), me.roles().isEmpty() ? Set.of("-") : me.roles());
    }

    static ApprovalView view(RequestApproval a, ServiceRequest r) {
        return new ApprovalView(a.getId(), a.getRequestId(), r == null ? null : r.getRequestNo(), r == null ? null : r.getTitle(),
                a.getStepOrder(), a.getApproverId(), a.getApproverRole(), a.getDecision(), a.getComments(), a.getCreatedAt(),
                a.getDecidedAt());
    }
}
