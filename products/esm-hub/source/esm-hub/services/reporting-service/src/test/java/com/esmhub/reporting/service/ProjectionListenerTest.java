package com.esmhub.reporting.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.esmhub.common.contracts.DomainContracts.*;
import com.esmhub.common.events.EventEnvelope;
import com.esmhub.reporting.service.events.ProjectionListener;
import com.esmhub.reporting.service.events.ProjectionWriter;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import tools.jackson.databind.json.JsonMapper;

class ProjectionListenerTest {
    JsonMapper mapper = JsonMapper.builder().build();
    ProjectionWriter writer = mock(ProjectionWriter.class);
    ProjectionListener listener = new ProjectionListener(mapper, writer);

    String envelope(String type, Object payload) {
        return mapper.writeValueAsString(new EventEnvelope(UUID.randomUUID(), type, Instant.now(), 1L, null, null, "X", "1", 1,
                mapper.valueToTree(payload)));
    }

    ConsumerRecord<String, String> rec(String topic, String key, String value) {
        return new ConsumerRecord<>(topic, 0, 0L, key, value);
    }

    @Test
    void incidentSnapshotIsUpserted() {
        IncidentSnapshot s = new IncidentSnapshot(7, 1, "INC-7", "t", "NEW", false, "P2", 3L, "PORTAL", 2, null, null, Instant.now(),
                null, null, null, null, null, false, false, false, 0, null, 15);
        listener.onIncident(rec("incident.incidents", "7", envelope("incident.snapshot", s)));
        ArgumentCaptor<IncidentSnapshot> c = ArgumentCaptor.forClass(IncidentSnapshot.class);
        verify(writer).upsert(c.capture());
        assertThat(c.getValue().incidentId()).isEqualTo(7);
        assertThat(c.getValue().worklogMinutes()).isEqualTo(15);
    }

    @Test
    void tombstonesDeleteTheRowOfEachTopic() {
        listener.onIncident(rec("incident.incidents", "7", null));
        listener.onProblem(rec("incident.problems", "8", null));
        listener.onRequest(rec("request.requests", "9", null));
        listener.onChange(rec("change.changes", "10", null));
        listener.onAsset(rec("asset.assets", "11", null));
        verify(writer).delete("rpt_incidents", "incident_id", 7L);
        verify(writer).delete("rpt_problems", "problem_id", 8L);
        verify(writer).delete("rpt_requests", "request_id", 9L);
        verify(writer).delete("rpt_changes", "change_id", 10L);
        verify(writer).delete("rpt_assets", "asset_id", 11L);
    }

    @Test
    void otherSnapshotsAreRoutedToTheirUpsert() {
        listener.onProblem(rec("t", "1", envelope("problem.snapshot", new ProblemSnapshot(1, 1, "PRB-1", "t", "OPEN", true, null, Instant.now(), null, List.of(1L)))));
        listener.onRequest(rec("t", "1", envelope("request.snapshot", new RequestSnapshot(1, 1, "REQ-1", "t", "SUBMITTED", 2, null, null, BigDecimal.TEN, null, Instant.now(), null, null))));
        listener.onChange(rec("t", "1", envelope("change.snapshot", new ChangeSnapshot(1, 1, "CHG-1", "t", "NORMAL", "DRAFT", null, null, null, null, null, null, null, null, Instant.now()))));
        listener.onAsset(rec("t", "1", envelope("asset.snapshot", new AssetSnapshot(1, 1, "A-1", "LAPTOP", "IN_STOCK", null, null, null, null, null))));
        verify(writer).upsert(any(ProblemSnapshot.class));
        verify(writer).upsert(any(RequestSnapshot.class));
        verify(writer).upsert(any(ChangeSnapshot.class));
        verify(writer).upsert(any(AssetSnapshot.class));
    }
}
