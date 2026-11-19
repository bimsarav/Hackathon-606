package com.esmhub.request.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Topics owned by request-service plus the shared audit topic. */
@Configuration(proxyBeanMethods = false)
public class RequestTopics {
    @Bean
    KafkaAdmin.NewTopics requestTopicDefinitions() {
        return new KafkaAdmin.NewTopics(Topics.compacted(Topics.REQUEST_REQUESTS),
                Topics.events(Topics.REQUEST_EVENTS, 7), Topics.events(Topics.AUDIT_EVENTS, 30));
    }
}
