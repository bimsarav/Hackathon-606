package com.esmhub.notification.service.notification;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

public interface NotificationRepository extends JpaRepository<Notification, Long> {
    boolean existsByEventIdAndUserIdAndChannel(UUID eventId, long userId, String channel);

    Page<Notification> findByUserIdAndChannel(long userId, String channel, Pageable pageable);

    Page<Notification> findByUserIdAndChannelAndReadAtIsNull(long userId, String channel, Pageable pageable);

    long countByUserIdAndChannelAndReadAtIsNull(long userId, String channel);

    Optional<Notification> findByIdAndUserId(Long id, long userId);

    Optional<Notification> findByIdAndCompanyId(Long id, long companyId);

    Page<Notification> findByCompanyIdAndDeliveryStatus(long companyId, String status, Pageable pageable);

    @Modifying
    @Query("update Notification n set n.readAt = ?3 where n.userId = ?1 and n.channel = ?2 and n.readAt is null")
    int markAllRead(long userId, String channel, Instant now);

    /** Claims due emails; other sender instances skip rows locked here. */
    @Query(value = "SELECT * FROM notifications WHERE channel = 'EMAIL' AND delivery_status IN ('PENDING', 'FAILED') "
            + "AND next_attempt_at <= ?1 ORDER BY notification_id LIMIT ?2 FOR UPDATE SKIP LOCKED", nativeQuery = true)
    List<Notification> claimDueEmails(Instant now, int limit);
}
