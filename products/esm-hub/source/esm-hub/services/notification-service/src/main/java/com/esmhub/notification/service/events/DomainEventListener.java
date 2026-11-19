package com.esmhub.notification.service.events;

import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.events.EventReader;
import com.esmhub.common.events.Topics;
import com.esmhub.notification.service.notification.NotificationIngest;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/** Reads every *.events topic exactly once per eventId and stores the notifications. */
@Component
public class DomainEventListener {
    static final String CONSUMER = "notification-service.events";

    private final EventReader reader;
    private final NotificationIngest ingest;

    public DomainEventListener(EventReader reader, NotificationIngest ingest) {
        this.reader = reader;
        this.ingest = ingest;
    }

    @KafkaListener(topics = {Topics.INCIDENT_EVENTS, Topics.REQUEST_EVENTS, Topics.CHANGE_EVENTS, Topics.ASSET_EVENTS,
            Topics.KNOWLEDGE_EVENTS}, groupId = "${spring.application.name}.events", properties = "auto.offset.reset=earliest")
    public void onEvent(String json) {
        if (json == null) return;
        reader.once(CONSUMER, json, env ->
                ingest.ingest(env.eventId(), env.companyId(), reader.payload(env, DomainEvent.class)));
    }
}
