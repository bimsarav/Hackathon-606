package com.esmhub.change.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Topics owned by change-service plus the shared audit topic. */
@Configuration(proxyBeanMethods = false)
public class ChangeTopics {
    @Bean
    KafkaAdmin.NewTopics changeTopicDefinitions() {
        return new KafkaAdmin.NewTopics(Topics.compacted(Topics.CHANGE_CHANGES),
                Topics.events(Topics.CHANGE_EVENTS, 7), Topics.events(Topics.AUDIT_EVENTS, 30));
    }
}
