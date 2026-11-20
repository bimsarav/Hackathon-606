package com.esmhub.audit.service.events;

import com.esmhub.audit.service.audit.AuditStore;
import com.esmhub.common.audit.AuditPublisher.AuditPayload;
import com.esmhub.common.events.EventReader;
import com.esmhub.common.events.Topics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/** Reads audit.events exactly once per eventId and appends the record. */
@Component
public class AuditEventListener {
    private static final Logger log = LoggerFactory.getLogger(AuditEventListener.class);
    static final String CONSUMER = "audit-service.records";

    private final EventReader reader;
    private final AuditStore store;

    public AuditEventListener(EventReader reader, AuditStore store) {
        this.reader = reader;
        this.store = store;
    }

    @KafkaListener(topics = Topics.AUDIT_EVENTS, groupId = "${spring.application.name}.records",
            properties = "auto.offset.reset=earliest")
    public void onEvent(String json) {
        if (json == null) return;
        reader.once(CONSUMER, json, env -> {
            AuditPayload p = reader.payload(env, AuditPayload.class);
            if (env.companyId() == null) {
                log.warn("audit event {} has no company; stored but invisible to queries", env.eventId());
            }
            store.append(env, p);
        });
    }
}
