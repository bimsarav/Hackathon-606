package com.esmhub.notification.service.notification;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Used when no SMTP host is configured: logs metadata only (never the recipient address or body) and succeeds. */
public class LogSinkEmailSender implements EmailSender {
    private static final Logger log = LoggerFactory.getLogger(LogSinkEmailSender.class);

    @Override
    public void send(String to, String subject, String body) {
        log.info("email_sink_delivered subjectLength={} bodyLength={}", subject == null ? 0 : subject.length(),
                body == null ? 0 : body.length());
    }
}
