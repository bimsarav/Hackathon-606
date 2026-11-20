package com.esmhub.audit.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.audit.service.audit.AuditStore;
import com.esmhub.audit.service.events.AuditEventListener;
import com.esmhub.common.audit.AuditPublisher.AuditPayload;
import com.esmhub.common.events.EventEnvelope;
import com.esmhub.common.events.EventReader;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;

class AuditEventListenerTest {
    EventReader reader = mock(EventReader.class);
    AuditStore store = mock(AuditStore.class);
    AuditEventListener listener = new AuditEventListener(reader, store);

    @Test
    @SuppressWarnings("unchecked")
    void appendsParsedPayload() {
        var env = new EventEnvelope(UUID.randomUUID(), "audit.create", Instant.now(), 1L, 9L, "c1", "ASSET", "3", 1, null);
        var payload = new AuditPayload("asset-service", "ASSET", "3", "CREATE", null, Map.of("a", 1), "10.0.0.1");
        when(reader.once(any(), any(), any())).thenAnswer(inv -> {
            ((Consumer<EventEnvelope>) inv.getArgument(2)).accept(env);
            return true;
        });
        when(reader.payload(env, AuditPayload.class)).thenReturn(payload);
        listener.onEvent("{}");
        verify(store).append(env, payload);
    }

    @Test
    void tombstonesAreIgnored() {
        listener.onEvent(null);
        verifyNoInteractions(reader, store);
    }

    @Test
    void usesDedicatedConsumerName() {
        listener.onEvent("{}");
        verify(reader).once(eq("audit-service.records"), eq("{}"), any());
    }
}
