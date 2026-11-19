package com.esmhub.common.events;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.CurrentUserProvider;
import com.esmhub.common.web.RequestIdFilter;
import java.time.Instant;
import java.util.UUID;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/** Writes events into the outbox inside the caller's transaction. Business code never uses KafkaTemplate directly. */
public class OutboxPublisher {
    private final OutboxRepository repo;
    private final JsonMapper mapper;
    private final CurrentUserProvider users;

    public OutboxPublisher(OutboxRepository repo, JsonMapper mapper, CurrentUserProvider users) {
        this.repo = repo;
        this.mapper = mapper;
        this.users = users;
    }

    /** Domain event or state snapshot. {@code payload} is serialised to JSON. */
    @Transactional(propagation = Propagation.MANDATORY)
    public UUID publish(String topic, String eventType, String aggregateType, Object aggregateId, Long companyId, Object payload) {
        UUID id = UUID.randomUUID();
        Long actor = users.find().map(CurrentUser::userId).orElse(null);
        String corr = RequestIdFilter.current();
        EventEnvelope env = new EventEnvelope(id, eventType, Instant.now(), companyId, actor, corr, aggregateType,
                String.valueOf(aggregateId), 1, mapper.valueToTree(payload));
        repo.save(new OutboxEvent(id, topic, String.valueOf(aggregateId), eventType, mapper.writeValueAsString(env), corr));
        return id;
    }

    /** Deletes a key from a compacted state topic. */
    @Transactional(propagation = Propagation.MANDATORY)
    public void tombstone(String topic, String aggregateType, Object aggregateId) {
        repo.save(new OutboxEvent(UUID.randomUUID(), topic, String.valueOf(aggregateId), aggregateType + ".deleted", null,
                RequestIdFilter.current()));
    }
}
