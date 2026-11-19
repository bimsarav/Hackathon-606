package com.esmhub.notification.service.notification;

import com.esmhub.directory.DirectoryLookup;
import com.esmhub.directory.DirUser;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/** Sends due EMAIL notifications; failures back off exponentially and end DEAD after max-attempts. */
@Component
public class EmailDispatcher {
    private static final Logger log = LoggerFactory.getLogger(EmailDispatcher.class);

    private final NotificationRepository repo;
    private final DirectoryLookup directory;
    private final EmailSender sender;
    private final NotificationProperties props;
    private final TransactionTemplate tx;

    public EmailDispatcher(NotificationRepository repo, DirectoryLookup directory, EmailSender sender,
                           NotificationProperties props, TransactionTemplate tx) {
        this.repo = repo;
        this.directory = directory;
        this.sender = sender;
        this.props = props;
        this.tx = tx;
    }

    @Scheduled(fixedDelayString = "${esm.notification.poll-ms:5000}", initialDelayString = "${esm.notification.poll-ms:5000}")
    public void poll() {
        if (props.senderEnabledOrDefault()) {
            dispatchDue();
        }
    }

    /** Processes one batch; returns the number of rows handled. */
    public int dispatchDue() {
        Integer n = tx.execute(status -> process(repo.claimDueEmails(Instant.now(), props.batchSizeOrDefault())));
        return n == null ? 0 : n;
    }

    public int process(List<Notification> due) {
        for (Notification n : due) {
            Instant now = Instant.now();
            try {
                Optional<DirUser> user = directory.user(n.getUserId());
                if (user.isEmpty() || user.get().getEmail() == null) {
                    throw new IllegalStateException("recipient has no email address");
                }
                sender.send(user.get().getEmail(), n.getSubject(), n.getBody());
                n.recordSent(now);
            } catch (Exception e) {
                n.recordFailure(e.getClass().getSimpleName() + ": " + e.getMessage(), props.maxAttemptsOrDefault(), now);
                if (Notification.DEAD.equals(n.getDeliveryStatus())) {
                    log.error("email_dead notificationId={} attempts={}", n.getId(), n.getAttempts());
                } else {
                    log.warn("email_retry notificationId={} attempts={}", n.getId(), n.getAttempts());
                }
            }
        }
        repo.saveAll(due);
        return due.size();
    }
}
