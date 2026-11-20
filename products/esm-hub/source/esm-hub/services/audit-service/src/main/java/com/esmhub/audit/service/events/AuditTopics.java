package com.esmhub.audit.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** audit-service declares the shared audit topic (30 days retention; the store is the system of record). */
@Configuration(proxyBeanMethods = false)
public class AuditTopics {
    @Bean
    KafkaAdmin.NewTopics auditTopicDefinitions() {
        return new KafkaAdmin.NewTopics(Topics.events(Topics.AUDIT_EVENTS, 30));
    }
}
