package com.esmhub.notification.service.notification;

import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mail.javamail.JavaMailSender;

@Configuration(proxyBeanMethods = false)
public class MailConfig {
    /** SMTP when a JavaMailSender exists (spring.mail.host set), otherwise the log sink. */
    @Bean
    EmailSender emailSender(ObjectProvider<JavaMailSender> mail, NotificationProperties props) {
        JavaMailSender sender = mail.getIfAvailable();
        return sender == null ? new LogSinkEmailSender() : new SmtpEmailSender(sender, props.mailFromOrDefault());
    }
}
