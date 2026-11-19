package com.esmhub.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.notification.service.notification.Notification;
import com.esmhub.notification.service.notification.NotificationIngest;
import com.esmhub.notification.service.notification.NotificationRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class NotificationIngestTest {
    NotificationRepository repo = mock(NotificationRepository.class);
    DirectoryLookup dir = mock(DirectoryLookup.class);
    NotificationIngest ingest = new NotificationIngest(repo, dir);

    DirUser user(String status) {
        DirUser u = mock(DirUser.class);
        when(u.isActive()).thenReturn(!"INACTIVE".equals(status));
        return u;
    }

    @BeforeEach
    void users() {
        DirUser active = user("ACTIVE");
        DirUser inactive = user("INACTIVE");
        when(dir.userInCompany(eq(1L), anyLong())).thenReturn(Optional.of(active));
        when(dir.userInCompany(eq(2L), anyLong())).thenReturn(Optional.of(inactive));
        when(dir.userInCompany(eq(3L), anyLong())).thenReturn(Optional.empty()); // other company
    }

    DomainEvent event(boolean email, Long... ids) {
        return new DomainEvent("INCIDENT", "151", "INC-000151",
                new NotificationIntent(List.of(ids), "Subj", "Msg", "/incidents/151", email), Map.of());
    }

    @Test
    void filtersInactiveForeignUnknownAndDuplicates() {
        assertThat(ingest.eligibleRecipients(List.of(1L, 1L, 2L, 3L, 4L), 1L)).containsExactly(1L);
    }

    @Test
    void createsInAppAndEmailPerEligibleRecipient() {
        int n = ingest.ingest(UUID.randomUUID(), 1L, event(true, 1L, 2L, 3L));
        assertThat(n).isEqualTo(2);
        ArgumentCaptor<Notification> c = ArgumentCaptor.forClass(Notification.class);
        verify(repo, times(2)).save(c.capture());
        assertThat(c.getAllValues()).extracting(Notification::getChannel).containsExactly("IN_APP", "EMAIL");
    }

    @Test
    void noEmailWhenIntentSaysNo() {
        assertThat(ingest.ingest(UUID.randomUUID(), 1L, event(false, 1L))).isEqualTo(1);
    }

    @Test
    void existingDedupeKeySkipsCreation() {
        when(repo.existsByEventIdAndUserIdAndChannel(any(), anyLong(), any())).thenReturn(true);
        assertThat(ingest.ingest(UUID.randomUUID(), 1L, event(true, 1L))).isZero();
        verify(repo, never()).save(any());
    }

    @Test
    void missingCompanyOrNotificationCreatesNothing() {
        assertThat(ingest.ingest(UUID.randomUUID(), null, event(true, 1L))).isZero();
        assertThat(ingest.ingest(UUID.randomUUID(), 1L, new DomainEvent("X", "1", null, null, null))).isZero();
    }
}
