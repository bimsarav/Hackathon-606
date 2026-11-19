package com.esmhub.notification.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Declares (idempotently) the event topics this service reads, so listeners can start before the producers. */
@Configuration(proxyBeanMethods = false)
public class NotificationTopics {
    @Bean
    KafkaAdmin.NewTopics notificationTopicDefinitions() {
        return new KafkaAdmin.NewTopics(
                Topics.events(Topics.INCIDENT_EVENTS, 30), Topics.events(Topics.REQUEST_EVENTS, 30),
                Topics.events(Topics.CHANGE_EVENTS, 30), Topics.events(Topics.ASSET_EVENTS, 30),
                Topics.events(Topics.KNOWLEDGE_EVENTS, 30));
    }
}
