package com.esmhub.common.config;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.events.EventReader;
import com.esmhub.common.events.KafkaErrorHandling;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.OutboxRelay;
import com.esmhub.common.events.OutboxRepository;
import com.esmhub.common.events.ProcessedEventRepository;
import com.esmhub.common.events.SnapshotBootstrapper;
import com.esmhub.common.events.SnapshotSource;
import com.esmhub.common.events.SnapshotStateRepository;
import com.esmhub.common.security.CurrentUserArgumentResolver;
import com.esmhub.common.security.CurrentUserProvider;
import com.esmhub.common.security.EsmSecurityConfiguration;
import com.esmhub.common.web.GlobalExceptionHandler;
import com.esmhub.common.web.RequestIdFilter;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.AutoConfigurationPackage;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.core.Ordered;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import tools.jackson.databind.json.JsonMapper;

/** Wires the shared building blocks into every service that depends on esm-common. */
@AutoConfiguration
@AutoConfigurationPackage(basePackages = "com.esmhub.common.events")
@EnableScheduling
@Import({EsmSecurityConfiguration.class, GlobalExceptionHandler.class})
public class EsmCommonAutoConfiguration {

    @Bean
    FilterRegistrationBean<RequestIdFilter> esmRequestIdFilter() {
        FilterRegistrationBean<RequestIdFilter> reg = new FilterRegistrationBean<>(new RequestIdFilter());
        reg.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return reg;
    }

    @Bean
    @ConditionalOnMissingBean
    CurrentUserProvider currentUserProvider() { return new CurrentUserProvider(); }

    @Bean
    WebMvcConfigurer esmCurrentUserResolver(CurrentUserProvider provider) {
        return new WebMvcConfigurer() {
            @Override
            public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
                resolvers.add(new CurrentUserArgumentResolver(provider));
            }
        };
    }

    @Bean
    OutboxPublisher outboxPublisher(OutboxRepository repo, JsonMapper mapper, CurrentUserProvider users) {
        return new OutboxPublisher(repo, mapper, users);
    }

    @Bean
    @ConditionalOnProperty(name = "esm.outbox.relay-enabled", havingValue = "true", matchIfMissing = true)
    OutboxRelay outboxRelay(OutboxRepository repo, KafkaTemplate<String, String> kafka, TransactionTemplate tx) {
        return new OutboxRelay(repo, kafka, tx);
    }

    @Bean
    EventReader eventReader(JsonMapper mapper, ProcessedEventRepository processed) {
        return new EventReader(mapper, processed);
    }

    @Bean
    SnapshotBootstrapper snapshotBootstrapper(List<SnapshotSource> sources, SnapshotStateRepository states,
                                              OutboxPublisher publisher, TransactionTemplate tx) {
        return new SnapshotBootstrapper(sources, states, publisher, tx);
    }

    @Bean
    AuditPublisher auditPublisher(OutboxPublisher publisher, CurrentUserProvider users,
                                  @Value("${spring.application.name:unknown}") String service) {
        return new AuditPublisher(publisher, users, service);
    }

    /** Used by Spring Kafka's listener container factory for every @KafkaListener: backoff, then DLT. */
    @Bean
    @ConditionalOnMissingBean
    DefaultErrorHandler esmKafkaErrorHandler(KafkaTemplate<String, String> template) {
        return KafkaErrorHandling.errorHandler(template);
    }
}
