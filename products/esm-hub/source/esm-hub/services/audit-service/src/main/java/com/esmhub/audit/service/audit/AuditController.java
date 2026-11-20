package com.esmhub.audit.service.audit;

import com.esmhub.audit.service.audit.AuditDtos.AuditFilter;
import com.esmhub.audit.service.audit.AuditDtos.AuditView;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import java.time.Instant;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/audit")
public class AuditController {
    private final AuditService service;

    public AuditController(AuditService service) { this.service = service; }

    @GetMapping
    public PageResponse<AuditView> list(CurrentUser me, @RequestParam(required = false) String service,
            @RequestParam(required = false) String entityType, @RequestParam(required = false) String entityId,
            @RequestParam(required = false) String action, @RequestParam(required = false) Long actorId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
            @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return this.service.search(me, new AuditFilter(service, entityType, entityId, action, actorId, from, to), page, size);
    }

    @GetMapping("/export")
    public ResponseEntity<byte[]> export(CurrentUser me, @RequestParam(required = false) String service,
            @RequestParam(required = false) String entityType, @RequestParam(required = false) String entityId,
            @RequestParam(required = false) String action, @RequestParam(required = false) Long actorId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to) {
        return this.service.export(me, new AuditFilter(service, entityType, entityId, action, actorId, from, to));
    }
}
