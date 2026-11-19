package com.esmhub.knowledge.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Topics produced by knowledge-service (no state topic) plus the shared audit topic. */
@Configuration(proxyBeanMethods = false)
public class KnowledgeTopics {
    @Bean
    KafkaAdmin.NewTopics knowledgeTopicDefinitions() {
        return new KafkaAdmin.NewTopics(Topics.events(Topics.KNOWLEDGE_EVENTS, 7), Topics.events(Topics.AUDIT_EVENTS, 30));
    }
}
