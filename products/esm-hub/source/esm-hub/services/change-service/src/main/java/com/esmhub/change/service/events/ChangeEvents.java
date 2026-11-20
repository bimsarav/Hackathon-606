package com.esmhub.change.service.events;

import com.esmhub.change.service.change.Change;
import com.esmhub.common.contracts.DomainContracts.ChangeSnapshot;
import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import org.springframework.stereotype.Component;

/** Publishes change snapshots (state topic) and domain events with notification recipients (via the outbox). */
@Component
public class ChangeEvents {
    private final OutboxPublisher outbox;

    public ChangeEvents(OutboxPublisher outbox) { this.outbox = outbox; }

    public void snapshot(Change c) { snapshot(outbox, c); }

    public void snapshot(OutboxPublisher pub, Change c) {
        pub.publish(Topics.CHANGE_CHANGES, "change.snapshot", "change", c.getId(), c.getCompanyId(),
                new ChangeSnapshot(c.getId(), c.getCompanyId(), c.getChangeNo(), c.getTitle(), c.getChangeType(), c.getStatus(),
                        c.getRiskLevel(), c.getImpact(), c.getOwnerTeamId(), c.getRequesterId(), c.getPlannedStart(),
                        c.getPlannedEnd(), c.getActualStart(), c.getActualEnd(), c.getCreatedAt()));
    }

    /** eventType is e.g. "change.approved". Nothing is published when there is nobody to notify. */
    public void notify(String eventType, Change c, Collection<Long> recipients, String subject, String message, String link) {
        List<Long> ids = new ArrayList<>(new TreeSet<>(recipients));
        if (ids.isEmpty()) return;
        outbox.publish(Topics.CHANGE_EVENTS, eventType, "change", c.getId(), c.getCompanyId(),
                new DomainEvent("CHANGE", String.valueOf(c.getId()), c.getChangeNo(),
                        new NotificationIntent(ids, subject, message, link, true),
                        Map.of("status", c.getStatus(), "changeType", c.getChangeType(), "requesterId", c.getRequesterId())));
    }
}
