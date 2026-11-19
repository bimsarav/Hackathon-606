package com.esmhub.asset.service.events;

import com.esmhub.common.events.Topics;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaAdmin;

/** Topics owned by asset-service plus the shared audit topic. */
@Configuration(proxyBeanMethods = false)
public class AssetTopics {
    @Bean
    KafkaAdmin.NewTopics assetTopicDefinitions() {
        return new KafkaAdmin.NewTopics(Topics.compacted(Topics.ASSET_ASSETS), Topics.events(Topics.ASSET_EVENTS, 7),
                Topics.events(Topics.AUDIT_EVENTS, 30));
    }
}
