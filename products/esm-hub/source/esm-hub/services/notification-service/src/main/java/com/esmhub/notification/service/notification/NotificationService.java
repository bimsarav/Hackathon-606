package com.esmhub.notification.service.notification;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.notification.service.notification.NotificationDtos.*;
import java.time.Instant;
import java.util.Set;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class NotificationService {
    static final Set<String> ADMIN_STATUSES = Set.of("DEAD", "FAILED", "PENDING", "SENT", "DELIVERED");

    private final NotificationRepository repo;
    private final DirectoryLookup directory;

    public NotificationService(NotificationRepository repo, DirectoryLookup directory) {
        this.repo = repo;
        this.directory = directory;
    }

    @Transactional(readOnly = true)
    public PageResponse<NotificationView> mine(CurrentUser me, boolean unread, int page, int size) {
        var pg = PageResponse.pageable(page, size, Sort.by(Sort.Direction.DESC, "id"));
        Page<Notification> p = unread
                ? repo.findByUserIdAndChannelAndReadAtIsNull(me.userId(), Notification.IN_APP, pg)
                : repo.findByUserIdAndChannel(me.userId(), Notification.IN_APP, pg);
        return PageResponse.of(p, NotificationView::of);
    }

    @Transactional(readOnly = true)
    public UnreadCount unreadCount(CurrentUser me) {
        return new UnreadCount(repo.countByUserIdAndChannelAndReadAtIsNull(me.userId(), Notification.IN_APP));
    }

    @Transactional
    public void markRead(CurrentUser me, long id) {
        Notification n = repo.findByIdAndUserId(id, me.userId()).orElseThrow(() -> new NotFoundException("Notification not found."));
        n.markRead(Instant.now());
    }

    @Transactional
    public void markAllRead(CurrentUser me) {
        repo.markAllRead(me.userId(), Notification.IN_APP, Instant.now());
    }

    @Transactional(readOnly = true)
    public PageResponse<AdminNotificationView> adminList(CurrentUser me, String status, int page, int size) {
        me.require(Role.ADMIN);
        String st = status == null || status.isBlank() ? "DEAD" : status.toUpperCase();
        if (!ADMIN_STATUSES.contains(st)) throw new BusinessRuleException("Unknown status " + status + ".");
        var pg = PageResponse.pageable(page, size, Sort.by(Sort.Direction.DESC, "id"));
        return PageResponse.of(repo.findByCompanyIdAndDeliveryStatus(me.companyId(), st, pg), this::adminView);
    }

    @Transactional
    public AdminNotificationView retry(CurrentUser me, long id) {
        me.require(Role.ADMIN);
        Notification n = repo.findByIdAndCompanyId(id, me.companyId()).orElseThrow(() -> new NotFoundException("Notification not found."));
        if (!n.isRetryable()) throw new BusinessRuleException("Only FAILED or DEAD email notifications can be retried.");
        n.requeue(Instant.now());
        return adminView(n);
    }

    private AdminNotificationView adminView(Notification n) {
        return new AdminNotificationView(n.getId(), n.getUserId(), directory.name(n.getUserId()), n.getChannel(),
                n.getSubject(), n.getDeliveryStatus(), n.getAttempts(), n.getNextAttemptAt(), n.getLastError(),
                n.getCreatedAt(), n.getSentAt());
    }
}
