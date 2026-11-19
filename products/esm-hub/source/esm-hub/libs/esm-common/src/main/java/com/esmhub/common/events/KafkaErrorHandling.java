package com.esmhub.common.events;

import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.listener.DeadLetterPublishingRecoverer;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.ExponentialBackOff;

/** Consumer error policy: exponential backoff 1 s → 30 s (5 attempts), then the record goes to {@code <topic>.DLT}. */
public final class KafkaErrorHandling {
    private KafkaErrorHandling() {}

    public static DefaultErrorHandler errorHandler(KafkaTemplate<String, String> template) {
        ExponentialBackOff backOff = new ExponentialBackOff(1_000L, 2.0);
        backOff.setMaxInterval(30_000L);
        backOff.setMaxAttempts(5);
        return new DefaultErrorHandler(new DeadLetterPublishingRecoverer(template), backOff);
    }
}
