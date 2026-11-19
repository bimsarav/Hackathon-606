package com.esmhub.reporting.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Declares (idempotently) the state topics read here, plus the shared audit topic used for export auditing. */
@Configuration(proxyBeanMethods = false)
public class ReportingTopics {
    @Bean
    KafkaAdmin.NewTopics reportingTopicDefinitions() {
        return new KafkaAdmin.NewTopics(
                Topics.compacted(Topics.INCIDENT_INCIDENTS), Topics.compacted(Topics.INCIDENT_PROBLEMS),
                Topics.compacted(Topics.REQUEST_REQUESTS), Topics.compacted(Topics.CHANGE_CHANGES),
                Topics.compacted(Topics.ASSET_ASSETS), Topics.events(Topics.AUDIT_EVENTS, 30));
    }
}
