package com.esmhub.request.service.events;

import com.esmhub.request.service.request.ServiceRequest;
import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.common.contracts.DomainContracts.RequestSnapshot;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Publishes request snapshots (state topic) and domain events with notification recipients (via the outbox). */
@Component
public class RequestEvents {
    private final OutboxPublisher outbox;

    public RequestEvents(OutboxPublisher outbox) { this.outbox = outbox; }

    public void snapshot(ServiceRequest r) { snapshot(outbox, r); }

    public void snapshot(OutboxPublisher pub, ServiceRequest r) {
        pub.publish(Topics.REQUEST_REQUESTS, "request.snapshot", "request", r.getId(), r.getCompanyId(),
                new RequestSnapshot(r.getId(), r.getCompanyId(), r.getRequestNo(), r.getTitle(), r.getStatus(),
                        r.getRequesterId(), r.getServiceId(), r.getItemId(), r.getEstimatedCost(), r.getAssignedTeamId(),
                        r.getRequestedAt(), r.getApprovedAt(), r.getFulfilledAt()));
    }

    /** eventType is e.g. "request.approved". Nothing is published when there is nobody to notify. */
    public void notify(String eventType, ServiceRequest r, Collection<Long> recipients, String subject, String message,
                       String link) {
        List<Long> ids = new ArrayList<>(new java.util.TreeSet<>(recipients));
        if (ids.isEmpty()) return;
        outbox.publish(Topics.REQUEST_EVENTS, eventType, "request", r.getId(), r.getCompanyId(),
                new DomainEvent("SERVICE_REQUEST", String.valueOf(r.getId()), r.getRequestNo(),
                        new NotificationIntent(ids, subject, message, link, true),
                        Map.of("status", r.getStatus(), "requesterId", r.getRequesterId())));
    }
}
