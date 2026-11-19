package com.esmhub.reporting.service.events;

import com.esmhub.common.contracts.DomainContracts.*;
import com.esmhub.common.events.EventEnvelope;
import com.esmhub.common.events.Topics;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/**
 * Applies the compacted state topics to the read model. State messages are idempotent upserts (last value per key wins),
 * null values are tombstones. Own consumer group, earliest offset, so a fresh read model is rebuilt from the topics.
 */
@Component
public class ProjectionListener {
    private static final String EARLIEST = "auto.offset.reset=earliest";
    private final JsonMapper mapper;
    private final ProjectionWriter writer;

    public ProjectionListener(JsonMapper mapper, ProjectionWriter writer) {
        this.mapper = mapper;
        this.writer = writer;
    }

    private <T> T payload(String json, Class<T> type) {
        EventEnvelope env = mapper.readValue(json, EventEnvelope.class);
        return mapper.treeToValue(env.payload(), type);
    }

    @Transactional
    @KafkaListener(topics = Topics.INCIDENT_INCIDENTS, groupId = "${spring.application.name}.projections", properties = EARLIEST)
    public void onIncident(ConsumerRecord<String, String> rec) {
        if (rec.value() == null) { writer.delete("rpt_incidents", "incident_id", Long.parseLong(rec.key())); return; }
        writer.upsert(payload(rec.value(), IncidentSnapshot.class));
    }

    @Transactional
    @KafkaListener(topics = Topics.INCIDENT_PROBLEMS, groupId = "${spring.application.name}.projections", properties = EARLIEST)
    public void onProblem(ConsumerRecord<String, String> rec) {
        if (rec.value() == null) { writer.delete("rpt_problems", "problem_id", Long.parseLong(rec.key())); return; }
        writer.upsert(payload(rec.value(), ProblemSnapshot.class));
    }

    @Transactional
    @KafkaListener(topics = Topics.REQUEST_REQUESTS, groupId = "${spring.application.name}.projections", properties = EARLIEST)
    public void onRequest(ConsumerRecord<String, String> rec) {
        if (rec.value() == null) { writer.delete("rpt_requests", "request_id", Long.parseLong(rec.key())); return; }
        writer.upsert(payload(rec.value(), RequestSnapshot.class));
    }

    @Transactional
    @KafkaListener(topics = Topics.CHANGE_CHANGES, groupId = "${spring.application.name}.projections", properties = EARLIEST)
    public void onChange(ConsumerRecord<String, String> rec) {
        if (rec.value() == null) { writer.delete("rpt_changes", "change_id", Long.parseLong(rec.key())); return; }
        writer.upsert(payload(rec.value(), ChangeSnapshot.class));
    }

    @Transactional
    @KafkaListener(topics = Topics.ASSET_ASSETS, groupId = "${spring.application.name}.projections", properties = EARLIEST)
    public void onAsset(ConsumerRecord<String, String> rec) {
        if (rec.value() == null) { writer.delete("rpt_assets", "asset_id", Long.parseLong(rec.key())); return; }
        writer.upsert(payload(rec.value(), AssetSnapshot.class));
    }
}
