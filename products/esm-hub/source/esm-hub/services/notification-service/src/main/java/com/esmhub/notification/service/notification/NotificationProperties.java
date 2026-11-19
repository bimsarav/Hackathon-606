package com.esmhub.notification.service.notification;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** esm.notification.* settings. */
@ConfigurationProperties("esm.notification")
public record NotificationProperties(Integer maxAttempts, Integer batchSize, Boolean senderEnabled, String mailFrom) {
    public int maxAttemptsOrDefault() { return maxAttempts == null ? 6 : maxAttempts; }
    public int batchSizeOrDefault() { return batchSize == null ? 50 : batchSize; }
    public boolean senderEnabledOrDefault() { return senderEnabled == null || senderEnabled; }
    public String mailFromOrDefault() { return mailFrom == null || mailFrom.isBlank() ? "no-reply@esm-hub.local" : mailFrom; }
}
