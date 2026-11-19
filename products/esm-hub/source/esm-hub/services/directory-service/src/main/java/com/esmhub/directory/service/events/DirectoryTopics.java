package com.esmhub.directory.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Topics owned by directory-service (compacted state) plus the shared audit topic. */
@Configuration(proxyBeanMethods = false)
public class DirectoryTopics {
    @Bean
    KafkaAdmin.NewTopics directoryTopicDefinitions() {
        return new KafkaAdmin.NewTopics(
                Topics.compacted(Topics.DIRECTORY_USERS), Topics.compacted(Topics.DIRECTORY_TEAMS),
                Topics.compacted(Topics.DIRECTORY_SERVICES), Topics.compacted(Topics.DIRECTORY_OFFICES),
                Topics.events(Topics.AUDIT_EVENTS, 30));
    }

}
