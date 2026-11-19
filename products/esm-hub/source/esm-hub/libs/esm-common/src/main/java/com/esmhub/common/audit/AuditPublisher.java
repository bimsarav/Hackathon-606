package com.esmhub.common.audit;

import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import com.esmhub.common.security.CurrentUserProvider;
import jakarta.servlet.http.HttpServletRequest;
import java.net.InetAddress;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * Records an audit event (FR-12) through the outbox, in the caller's transaction. Only changed fields are kept;
 * callers must not pass free-text bodies or secrets. audit-service stores the events append-only.
 */
public class AuditPublisher {
    private final OutboxPublisher outbox;
    private final CurrentUserProvider users;
    private final String service;

    public AuditPublisher(OutboxPublisher outbox, CurrentUserProvider users, String service) {
        this.outbox = outbox;
        this.users = users;
        this.service = service;
    }

    public record AuditPayload(String service, String entityType, String entityId, String action,
                               Map<String, Object> oldValues, Map<String, Object> newValues, String sourceIp) {}

    @Transactional(propagation = Propagation.MANDATORY)
    public void record(String entityType, Object entityId, String action, Map<String, ?> before, Map<String, ?> after) {
        Map<String, Object> oldV = new LinkedHashMap<>();
        Map<String, Object> newV = new LinkedHashMap<>();
        if (before != null && after != null) {
            after.forEach((k, v) -> {
                if (!Objects.equals(before.get(k), v)) {
                    oldV.put(k, before.get(k));
                    newV.put(k, v);
                }
            });
        } else {
            if (before != null) oldV.putAll(before);
            if (after != null) newV.putAll(after);
        }
        Long company = users.find().map(u -> u.companyId()).orElse(null);
        outbox.publish(Topics.AUDIT_EVENTS, "audit." + action.toLowerCase(), entityType, entityId, company,
                new AuditPayload(service, entityType, String.valueOf(entityId), action,
                        oldV.isEmpty() ? null : oldV, newV.isEmpty() ? null : newV, clientIp()));
    }

    static String clientIp() {
        if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attrs) {
            HttpServletRequest req = attrs.getRequest();
            String fwd = req.getHeader("X-Forwarded-For");
            String ip = fwd != null && !fwd.isBlank() ? fwd.split(",")[0].trim() : req.getRemoteAddr();
            try {
                return InetAddress.ofLiteral(ip).getHostAddress();
            } catch (IllegalArgumentException e) {
                return null;
            }
        }
        return null;
    }
}
