package com.esmhub.request.service.approval;

import com.esmhub.request.service.approval.ApprovalDtos.*;
import com.esmhub.common.security.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/approvals")
public class ApprovalController {
    private final ApprovalService service;

    public ApprovalController(ApprovalService service) { this.service = service; }

    @GetMapping
    public List<ApprovalView> pending(CurrentUser me) { return service.pending(me); }

    @PostMapping("/{id}/decision")
    public ApprovalView decide(CurrentUser me, @PathVariable long id, @Valid @RequestBody DecisionIn body) {
        return service.decide(me, id, body.decision(), body.comments());
    }
}
