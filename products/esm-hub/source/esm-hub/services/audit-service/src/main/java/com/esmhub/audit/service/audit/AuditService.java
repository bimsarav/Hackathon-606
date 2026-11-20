package com.esmhub.audit.service.audit;

import com.esmhub.audit.service.audit.AuditDtos.AuditFilter;
import com.esmhub.audit.service.audit.AuditDtos.AuditView;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.CsvWriter;
import com.esmhub.common.web.PageResponse;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuditService {
    static final Role[] READERS = {Role.AUDITOR, Role.ADMIN};
    static final int EXPORT_MAX_ROWS = 10_000;

    private final AuditStore store;
    private final AuditPublisher audit;

    public AuditService(AuditStore store, AuditPublisher audit) {
        this.store = store;
        this.audit = audit;
    }

    @Transactional(readOnly = true)
    public PageResponse<AuditView> search(CurrentUser me, AuditFilter f, int page, int size) {
        me.require(READERS);
        var pageable = PageResponse.pageable(page, size, org.springframework.data.domain.Sort.unsorted());
        List<AuditView> items = store.find(me.companyId(), f, pageable.getPageSize(), pageable.getOffset());
        return new PageResponse<>(items, store.count(me.companyId(), f), page, size);
    }

    /** Exporting the audit trail is itself audited (the event comes back through Kafka into the store). */
    @Transactional
    public ResponseEntity<byte[]> export(CurrentUser me, AuditFilter f) {
        me.require(READERS);
        List<AuditView> rows = store.find(me.companyId(), f, EXPORT_MAX_ROWS, 0);
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("rows", rows.size());
        if (f.entityType() != null) details.put("entityType", f.entityType());
        if (f.action() != null) details.put("action", f.action());
        audit.record("AUDIT", 0, "EXPORT", null, details);
        List<List<?>> out = rows.stream().<List<?>>map(r -> List.of(r.auditId(), r.occurredAt(), r.service(),
                r.actorUserId() == null ? "" : r.actorUserId(), r.entityType(), r.entityId(), r.action(),
                r.sourceIp() == null ? "" : r.sourceIp(), r.oldValues() == null ? "" : r.oldValues().toString(),
                r.newValues() == null ? "" : r.newValues().toString())).toList();
        return CsvWriter.response("audit.csv", List.of("audit_id", "occurred_at", "service", "actor_user_id", "entity_type",
                "entity_id", "action", "source_ip", "old_values", "new_values"), out);
    }
}
