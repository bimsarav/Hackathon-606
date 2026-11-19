package com.esmhub.common.events;

import java.util.function.Consumer;
import org.slf4j.MDC;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/**
 * Parses envelopes and runs handlers exactly once per (eventId, consumer). The handler and the processed marker
 * commit in the same transaction, so a redelivery after a crash is skipped only if the work was committed.
 */
public class EventReader {
    private final JsonMapper mapper;
    private final ProcessedEventRepository processed;

    public EventReader(JsonMapper mapper, ProcessedEventRepository processed) {
        this.mapper = mapper;
        this.processed = processed;
    }

    public EventEnvelope parse(String json) {
        return mapper.readValue(json, EventEnvelope.class);
    }

    /** Returns false if already processed by this consumer. Tombstones (null values) must be handled by the caller. */
    @Transactional
    public boolean once(String consumer, String json, Consumer<EventEnvelope> handler) {
        EventEnvelope env = parse(json);
        ProcessedEvent.Key key = new ProcessedEvent.Key(env.eventId(), consumer);
        if (processed.existsById(key)) {
            return false;
        }
        String prev = MDC.get("requestId");
        try {
            if (env.correlationId() != null) {
                MDC.put("requestId", env.correlationId());
            }
            handler.accept(env);
            processed.save(new ProcessedEvent(env.eventId(), consumer));
            return true;
        } finally {
            if (prev == null) MDC.remove("requestId"); else MDC.put("requestId", prev);
        }
    }

    public <T> T payload(EventEnvelope env, Class<T> type) {
        return mapper.treeToValue(env.payload(), type);
    }
}
