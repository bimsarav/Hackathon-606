package com.esmhub.common.events;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.transaction.support.TransactionTemplate;

/** Publishes outbox rows to Kafka in id order (at-least-once). Stops a batch at the first failure to keep order. */
public class OutboxRelay {
    private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);
    static final int BATCH = 200;
    private final OutboxRepository repo;
    private final KafkaTemplate<String, String> kafka;
    private final TransactionTemplate tx;

    public OutboxRelay(OutboxRepository repo, KafkaTemplate<String, String> kafka, TransactionTemplate tx) {
        this.repo = repo;
        this.kafka = kafka;
        this.tx = tx;
    }

    @Scheduled(fixedDelayString = "${esm.outbox.poll-ms:500}", initialDelayString = "${esm.outbox.initial-delay-ms:2000}")
    public void relay() {
        Integer sent;
        do {
            sent = tx.execute(status -> relayBatch());
        } while (sent != null && sent == BATCH);
    }

    /** Returns the number sent, or -1 if the batch stopped at a failure. */
    int relayBatch() {
        List<OutboxEvent> batch = repo.lockBatch();
        int sent = 0;
        for (OutboxEvent e : batch) {
            try {
                ProducerRecord<String, String> rec = new ProducerRecord<>(e.getTopic(), e.getMessageKey(), e.getPayload());
                if (e.getCorrelationId() != null) {
                    rec.headers().add("correlationId", e.getCorrelationId().getBytes(StandardCharsets.UTF_8));
                }
                rec.headers().add("eventType", e.getEventType().getBytes(StandardCharsets.UTF_8));
                kafka.send(rec).get(10, TimeUnit.SECONDS);
                e.markPublished();
                sent++;
            } catch (Exception ex) {
                if (ex instanceof InterruptedException) {
                    Thread.currentThread().interrupt();
                }
                e.markFailed(ex.getClass().getSimpleName() + ": " + ex.getMessage());
                log.warn("outbox_publish_failed eventId={} topic={} attempts={}", e.getEventId(), e.getTopic(), e.getAttempts());
                return -1;
            }
        }
        return sent;
    }
}
