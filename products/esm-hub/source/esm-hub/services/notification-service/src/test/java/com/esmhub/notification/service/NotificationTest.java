package com.esmhub.notification.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.notification.service.notification.Notification;
import java.time.Duration;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class NotificationTest {
    Notification email() {
        return new Notification(1, 2, Notification.EMAIL, "s", "b", null, null, null, null, null);
    }

    @Test
    void backoffDoublesAndCapsAtSixtyMinutes() {
        assertThat(Notification.backoff(1)).isEqualTo(Duration.ofMinutes(2));
        assertThat(Notification.backoff(3)).isEqualTo(Duration.ofMinutes(8));
        assertThat(Notification.backoff(5)).isEqualTo(Duration.ofMinutes(32));
        assertThat(Notification.backoff(6)).isEqualTo(Duration.ofMinutes(60));
        assertThat(Notification.backoff(40)).isEqualTo(Duration.ofMinutes(60));
    }

    @Test
    void failureSchedulesRetryUntilMaxAttemptsThenDead() {
        Notification n = email();
        Instant now = Instant.parse("2026-01-01T00:00:00Z");
        n.recordFailure("boom", 3, now);
        assertThat(n.getDeliveryStatus()).isEqualTo("FAILED");
        assertThat(n.getNextAttemptAt()).isEqualTo(now.plus(Duration.ofMinutes(2)));
        n.recordFailure("boom", 3, now);
        assertThat(n.getDeliveryStatus()).isEqualTo("FAILED");
        n.recordFailure("boom", 3, now);
        assertThat(n.getDeliveryStatus()).isEqualTo("DEAD");
        assertThat(n.getAttempts()).isEqualTo(3);
        assertThat(n.getLastError()).isEqualTo("boom");
    }

    @Test
    void requeueResetsAndOnlyFailedOrDeadAreRetryable() {
        Notification n = email();
        assertThat(n.isRetryable()).isFalse();
        n.recordFailure("x", 1, Instant.now());
        assertThat(n.isRetryable()).isTrue();
        n.requeue(Instant.now());
        assertThat(n.getDeliveryStatus()).isEqualTo("PENDING");
        assertThat(n.getAttempts()).isZero();
        assertThat(n.getLastError()).isNull();
    }

    @Test
    void inAppIsDeliveredAtOnceAndEmailPending() {
        assertThat(new Notification(1, 2, Notification.IN_APP, "s", "b", null, null, null, null, null).getDeliveryStatus())
                .isEqualTo("DELIVERED");
        assertThat(email().getDeliveryStatus()).isEqualTo("PENDING");
    }
}
