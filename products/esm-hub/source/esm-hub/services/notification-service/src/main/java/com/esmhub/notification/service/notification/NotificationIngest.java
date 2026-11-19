package com.esmhub.notification.service.notification;

import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.directory.DirectoryLookup;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** Turns a domain event's notification intent into per-recipient IN_APP and EMAIL rows. */
@Service
public class NotificationIngest {
    private static final Logger log = LoggerFactory.getLogger(NotificationIngest.class);

    private final NotificationRepository repo;
    private final DirectoryLookup directory;

    public NotificationIngest(NotificationRepository repo, DirectoryLookup directory) {
        this.repo = repo;
        this.directory = directory;
    }

    /** Recipients that exist, are active and belong to the event's company (unknown or foreign users are dropped). */
    public Set<Long> eligibleRecipients(List<Long> ids, long companyId) {
        Set<Long> out = new LinkedHashSet<>();
        if (ids == null) return out;
        for (Long id : ids) {
            if (id != null && directory.userInCompany(id, companyId).filter(u -> u.isActive()).isPresent()) {
                out.add(id);
            }
        }
        return out;
    }

    /** Returns the number of notifications created. Safe to call twice for the same event (dedupe per channel). */
    public int ingest(UUID eventId, Long companyId, DomainEvent event) {
        NotificationIntent intent = event == null ? null : event.notification();
        if (intent == null || intent.notifyUserIds() == null || intent.notifyUserIds().isEmpty()) return 0;
        if (companyId == null) {
            log.warn("notification_skipped_no_company eventId={}", eventId);
            return 0;
        }
        int created = 0;
        for (Long userId : eligibleRecipients(intent.notifyUserIds(), companyId)) {
            created += create(eventId, companyId, userId, Notification.IN_APP, intent, event);
            if (intent.email()) {
                created += create(eventId, companyId, userId, Notification.EMAIL, intent, event);
            }
        }
        return created;
    }

    private int create(UUID eventId, Long companyId, long userId, String channel, NotificationIntent in, DomainEvent ev) {
        if (eventId != null && repo.existsByEventIdAndUserIdAndChannel(eventId, userId, channel)) return 0;
        repo.save(new Notification(companyId, userId, channel, in.subject(), in.message(), in.link(), ev.reference(),
                ev.entityType(), ev.entityId(), eventId));
        return 1;
    }
}
