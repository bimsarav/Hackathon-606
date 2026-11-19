package com.esmhub.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.notification.service.notification.*;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class EmailDispatcherTest {
    NotificationRepository repo = mock(NotificationRepository.class);
    DirectoryLookup dir = mock(DirectoryLookup.class);
    EmailSender sender = mock(EmailSender.class);
    NotificationProperties props = new NotificationProperties(2, 10, true, null);
    EmailDispatcher dispatcher = new EmailDispatcher(repo, dir, sender, props, null);

    Notification email() {
        DirUser u = mock(DirUser.class);
        when(u.getEmail()).thenReturn("a@example.test");
        when(dir.user(5L)).thenReturn(Optional.of(u));
        return new Notification(1, 5, Notification.EMAIL, "s", "b", null, null, null, null, null);
    }

    @Test
    void successMarksSent() {
        Notification n = email();
        dispatcher.process(List.of(n));
        verify(sender).send("a@example.test", "s", "b");
        assertThat(n.getDeliveryStatus()).isEqualTo("SENT");
        assertThat(n.getSentAt()).isNotNull();
    }

    @Test
    void failuresRetryThenDead() {
        Notification n = email();
        doThrow(new IllegalStateException("smtp down")).when(sender).send(any(), any(), any());
        dispatcher.process(List.of(n));
        assertThat(n.getDeliveryStatus()).isEqualTo("FAILED");
        dispatcher.process(List.of(n));
        assertThat(n.getDeliveryStatus()).isEqualTo("DEAD");
        assertThat(n.getLastError()).contains("smtp down");
    }

    @Test
    void missingRecipientIsAFailure() {
        when(dir.user(9L)).thenReturn(Optional.empty());
        Notification n = new Notification(1, 9, Notification.EMAIL, "s", "b", null, null, null, null, null);
        dispatcher.process(List.of(n));
        assertThat(n.getDeliveryStatus()).isEqualTo("FAILED");
        verifyNoInteractions(sender);
    }
}
