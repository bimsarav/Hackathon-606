package com.esmhub.incident.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Topics owned by incident-service: two compacted state topics and the domain-event topic. */
@Configuration(proxyBeanMethods = false)
public class IncidentTopics {
    @Bean
    KafkaAdmin.NewTopics incidentTopicDefinitions() {
        return new KafkaAdmin.NewTopics(Topics.compacted(Topics.INCIDENT_INCIDENTS),
                Topics.compacted(Topics.INCIDENT_PROBLEMS), Topics.events(Topics.INCIDENT_EVENTS, 30));
    }
}
