package com.esmhub.change.service.approval;

import com.esmhub.change.service.approval.ApprovalDtos.ApprovalView;
import com.esmhub.change.service.approval.ChangePolicy.Step;
import com.esmhub.change.service.change.Change;
import com.esmhub.change.service.change.ChangeRepository;
import com.esmhub.change.service.events.ChangeEvents;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirectoryLookup;
import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Opens approval steps and records decisions. Rules live in {@link ChangePolicy}. */
@Service
public class ApprovalService {
    private final ChangeApprovalRepository approvals;
    private final ChangeRepository changes;
    private final DirectoryLookup directory;
    private final ChangeEvents events;
    private final AuditPublisher audit;

    public ApprovalService(ChangeApprovalRepository approvals, ChangeRepository changes, DirectoryLookup directory,
                           ChangeEvents events, AuditPublisher audit) {
        this.approvals = approvals;
        this.changes = changes;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
    }

    public List<Step> stepsFor(Change c) { return ChangePolicy.steps(c.getChangeType(), c.getRiskLevel()); }

    /** Creates the pending approval for a step and notifies the approvers (never the requester). */
    public ChangeApproval openStep(Change c, Step step, Instant now) {
        ChangeApproval a = approvals.save(new ChangeApproval(c.getId(), step.order(), step.role(), now));
        Set<Long> recipients = new HashSet<>(directory.activeUserIdsWithRole(c.getCompanyId(), step.role()));
        recipients.remove(c.getRequesterId());
        events.notify("change.approval_requested", c, recipients, "Approval needed: " + c.getChangeNo(), c.getTitle(), "/approvals");
        return a;
    }

    @Transactional(readOnly = true)
    public List<ApprovalView> pending(CurrentUser me) {
        Set<String> roles = me.roles().isEmpty() ? Set.of("-") : me.roles();
        return approvals.pendingFor(me.companyId(), me.userId(), roles).stream().map(a -> Map.entry(a, changes.findById(a.getChangeId())))
                .filter(e -> e.getValue().isPresent())
                .filter(e -> ChangePolicy.canDecide(e.getKey(), e.getValue().get().getRequesterId(), me))
                .map(e -> view(e.getKey(), e.getValue().get())).toList();
    }

    @Transactional
    public ApprovalView decide(CurrentUser me, long approvalId, String decision, String comments) {
        ChangeApproval a = approvals.lockById(approvalId).orElseThrow(() -> NotFoundException.of("Approval", approvalId));
        Change c = changes.findById(a.getChangeId()).filter(x -> x.getCompanyId() == me.companyId())
                .orElseThrow(() -> NotFoundException.of("Approval", approvalId));
        if (!a.isPending()) throw new ConflictException("This approval has already been decided.");
        if (!ChangePolicy.canDecide(a, c.getRequesterId(), me)) throw new ForbiddenException("You are not an approver for this step.");
        Instant now = Instant.now();
        a.decide(decision, comments, me.userId(), now);
        audit.record("CHANGE", c.getId(), "APPROVAL_" + decision, null, Map.of("approvalId", a.getId(), "step", a.getStepOrder()));
        String link = "/changes/" + c.getId();
        Set<Long> interested = new HashSet<>(Set.of(c.getRequesterId()));
        interested.addAll(directory.teamLead(c.getOwnerTeamId()));
        if ("REJECTED".equals(decision)) {
            c.setStatus("REJECTED", now);
            events.notify("change.rejected", c, interested, c.getChangeNo() + " was rejected", comments == null ? "" : comments, link);
        } else {
            int done = a.getStepOrder();
            Optional<Step> next = stepsFor(c).stream().filter(s -> s.order() > done).findFirst();
            if (next.isPresent()) {
                openStep(c, next.get(), now);
            } else {
                c.setStatus("SCHEDULED", now);
                events.notify("change.approved", c, interested, c.getChangeNo() + " approved", c.getTitle(), link);
            }
        }
        changes.save(c);
        events.snapshot(c);
        return view(a, c);
    }

    /** Cancelling a change closes its open approvals. */
    public void cancelPending(Change c, long by, Instant now) {
        for (ChangeApproval a : approvals.findByChangeIdAndDecision(c.getId(), "PENDING")) {
            a.decide("REJECTED", "Change cancelled", by, now);
        }
    }

    public List<ChangeApproval> chain(long changeId) { return approvals.findByChangeIdOrderByStepOrderAscIdAsc(changeId); }

    public boolean involves(long changeId, CurrentUser me) {
        return approvals.involves(changeId, me.userId(), me.roles().isEmpty() ? Set.of("-") : me.roles());
    }

    static ApprovalView view(ChangeApproval a, Change c) {
        return new ApprovalView(a.getId(), a.getChangeId(), c == null ? null : c.getChangeNo(), c == null ? null : c.getTitle(),
                c == null ? null : c.getChangeType(), c == null ? null : c.getRiskLevel(), a.getStepOrder(), a.getApproverId(),
                a.getApproverRole(), a.getDecision(), a.getComments(), a.getCreatedAt(), a.getDecidedAt());
    }
}
