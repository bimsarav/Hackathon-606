package com.esmhub.testsupport;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.postgresql.PostgreSQLContainer;

/**
 * Import in integration tests: {@code @Import(EsmContainers.class)}. Containers are shared per JVM (static) and wired to
 * Spring Boot through {@code @ServiceConnection}, so no URLs need to be configured.
 */
@TestConfiguration(proxyBeanMethods = false)
public class EsmContainers {
    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:16-alpine");
    static final KafkaContainer KAFKA = new KafkaContainer("apache/kafka:4.4.0");

    static {
        POSTGRES.start();
        KAFKA.start();
    }

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() { return POSTGRES; }

    @Bean
    @ServiceConnection
    KafkaContainer kafka() { return KAFKA; }
}
