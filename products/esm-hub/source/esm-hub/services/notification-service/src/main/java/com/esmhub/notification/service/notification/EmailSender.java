package com.esmhub.notification.service.notification;

/** Delivers one email. Throws on failure; the dispatcher records the error and retries. */
public interface EmailSender {
    void send(String to, String subject, String body);
}
