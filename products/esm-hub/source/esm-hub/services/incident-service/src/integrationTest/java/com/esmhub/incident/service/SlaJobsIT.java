package com.esmhub.incident.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.common.events.Topics;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.incident.service.events.IncidentSnapshotSource;
import com.esmhub.incident.service.jobs.SlaJobs;
import com.esmhub.testsupport.EsmContainers;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.transaction.support.TransactionTemplate;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class SlaJobsIT extends IncidentTestBase {
    @Autowired SlaJobs jobs;
    @Autowired IncidentSnapshotSource source;
    @Autowired OutboxPublisher publisher;
    @Autowired TransactionTemplate tx;

    @BeforeAll
    void seed() { seedDirectory(); }

    long p2Incident() throws Exception {
        return createIncident(agent, "{\"title\":\"Core switch down\",\"description\":\"Floor 3 offline\",\"serviceId\":1,\"priorityId\":2}");
    }

    @Test
    void breachEscalatesToLeadsManagersAndAssigneeExactlyOnce() throws Exception {
        long id = p2Incident();
        postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        jdbc.update("UPDATE incidents SET response_due_at = now() - interval '2 hours', due_at = now() - interval '1 minute' WHERE incident_id = ?", id);

        assertThat(jobs.scanSla()).isGreaterThanOrEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT response_breached AND resolution_breached FROM incidents WHERE incident_id = ?", Boolean.class, id)).isTrue();
        assertThat(jdbc.queryForList("SELECT trigger_type FROM incident_escalations WHERE incident_id = ? ORDER BY 1", String.class, id))
                .containsExactly("RESOLUTION_BREACH", "RESPONSE_BREACH");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM incident_events WHERE incident_id = ? AND event_type = 'SLA_ESCALATED'", Integer.class, id)).isEqualTo(2);

        int again = jobs.scanSla();
        assertThat(again).isZero(); // already flagged: nothing is escalated a second time
        assertThat(jdbc.queryForObject("SELECT count(*) FROM incident_escalations WHERE incident_id = ?", Integer.class, id)).isEqualTo(2);

        List<String> escalations = drain(Topics.INCIDENT_EVENTS).stream()
                .filter(s -> s.startsWith(id + "\t") && s.contains("incident.sla_escalated")).toList();
        assertThat(escalations).hasSize(2);
        String all = String.join("\n", escalations);
        assertThat(all).contains("RESPONSE_BREACH").contains("RESOLUTION_BREACH");
        assertThat(escalations.stream().filter(s -> s.contains("RESPONSE_BREACH")).findFirst().orElseThrow())
                .contains("\"notifyUserIds\":[6,20]"); // assignee and team lead
        assertThat(escalations.stream().filter(s -> s.contains("\"trigger\":\"RESOLUTION_BREACH\"")).findFirst().orElseThrow())
                .contains("\"notifyUserIds\":[6,30]"); // assignee and service manager (P2 resolution breach)

        String snapshot = drain(Topics.INCIDENT_INCIDENTS).stream().filter(s -> s.startsWith(id + "\t")).reduce((a, b) -> b).orElseThrow();
        assertThat(snapshot).contains("\"responseBreached\":true").contains("\"resolutionBreached\":true");
    }

    @Test
    void pausedIncidentIsNotBreachedAndResolvedOnesAreIgnored() throws Exception {
        long paused = p2Incident();
        postJ("/api/v1/incidents/" + paused + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        moveTo(paused, tech6, "IN_PROGRESS", 200);
        moveTo(paused, tech6, "PENDING_USER", 200);
        jdbc.update("UPDATE incidents SET response_due_at = now() - interval '2 hours', due_at = now() - interval '1 minute' WHERE incident_id = ?", paused);
        long resolved = p2Incident();
        postJ("/api/v1/incidents/" + resolved + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        moveTo(resolved, tech6, "IN_PROGRESS", 200);
        resolve(resolved);
        jdbc.update("UPDATE incidents SET due_at = now() - interval '1 minute' WHERE incident_id = ?", resolved);
        jobs.scanSla();
        assertThat(jdbc.queryForObject("SELECT resolution_breached FROM incidents WHERE incident_id = ?", Boolean.class, paused)).isFalse();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM incident_escalations WHERE incident_id = ?", Integer.class, resolved)).isZero();
    }

    @Test
    void atRiskEscalatesOnceBeforeTheBreach() throws Exception {
        // a calendar-time policy for P2 on service 1, so 90% of the resolution target can be simulated without business hours
        jdbc.update("INSERT INTO sla_policies (company_id, name, priority_id, service_id, business_hours_only, response_target_minutes, "
                + "resolution_target_minutes, effective_from, version) VALUES (1, 'P2 calendar time', 2, 1, false, 30, 480, DATE '2026-01-01', 1)");
        long id = p2Incident();
        postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        moveTo(id, tech6, "IN_PROGRESS", 200);
        jdbc.update("UPDATE incidents SET created_at = now() - interval '430 minutes', due_at = now() + interval '50 minutes', "
                + "response_due_at = now() - interval '400 minutes' WHERE incident_id = ?", id);
        jobs.scanSla();
        jobs.scanSla();
        assertThat(jdbc.queryForList("SELECT trigger_type FROM incident_escalations WHERE incident_id = ?", String.class, id))
                .containsExactly("RESOLUTION_AT_RISK");
        assertThat(jdbc.queryForObject("SELECT resolution_breached FROM incidents WHERE incident_id = ?", Boolean.class, id)).isFalse();
    }

    @Test
    void autoCloseClosesOnlyIncidentsResolvedLongAgo() throws Exception {
        long old = p2Incident();
        postJ("/api/v1/incidents/" + old + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        moveTo(old, tech6, "IN_PROGRESS", 200);
        resolve(old);
        long recent = p2Incident();
        postJ("/api/v1/incidents/" + recent + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        moveTo(recent, tech6, "IN_PROGRESS", 200);
        resolve(recent);
        jdbc.update("UPDATE incidents SET resolved_at = now() - interval '4 days' WHERE incident_id = ?", old);

        assertThat(jobs.autoClose()).isGreaterThanOrEqualTo(1);
        assertThat(getJ("/api/v1/incidents/" + old, agent, 200).get("status").asString()).isEqualTo("CLOSED");
        assertThat(getJ("/api/v1/incidents/" + recent, agent, 200).get("status").asString()).isEqualTo("RESOLVED");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM incident_events WHERE incident_id = ? AND event_type = 'STATUS_CHANGE' AND to_value = 'CLOSED' AND actor_id IS NULL",
                Integer.class, old)).isEqualTo(1);
    }

    @Test
    void snapshotSourceRepublishesExistingIncidents() throws Exception {
        long id = p2Incident();
        long before = drain(Topics.INCIDENT_INCIDENTS).stream().filter(s -> s.startsWith(id + "\t")).count();
        tx.executeWithoutResult(s -> source.publishAll(publisher));
        long after = drain(Topics.INCIDENT_INCIDENTS).stream().filter(s -> s.startsWith(id + "\t")).count();
        assertThat(source.name()).isEqualTo("incident");
        assertThat(after).isEqualTo(before + 1);
    }
}
