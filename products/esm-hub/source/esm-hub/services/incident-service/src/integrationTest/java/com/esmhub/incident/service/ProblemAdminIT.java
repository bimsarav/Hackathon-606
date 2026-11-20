package com.esmhub.incident.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.esmhub.common.events.Topics;
import com.esmhub.testsupport.EsmContainers;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import tools.jackson.databind.JsonNode;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class ProblemAdminIT extends IncidentTestBase {
    @BeforeAll
    void seed() { seedDirectory(); }

    // ---------- problems ----------
    @Test
    void problemLifecycleWithKnownErrorLinksAndKafkaSnapshot() throws Exception {
        long inc1 = createIncident(eve);
        long inc2 = createIncident(evan);
        JsonNode p = postJ("/api/v1/problems", agent, "{\"title\":\"Recurring mail outage\",\"ownerTeamId\":1,\"incidentIds\":[" + inc1 + "]}", 201);
        long id = p.get("id").asLong();
        assertThat(p.get("problemNo").asString()).matches("PRB-\\d{5}");
        assertThat(p.get("status").asString()).isEqualTo("OPEN");
        assertThat(p.get("incidentCount").asInt()).isEqualTo(1);

        JsonNode linked = postJ("/api/v1/problems/" + id + "/incidents", tech6, "{\"incidentIds\":[" + inc2 + "]}", 200);
        assertThat(linked.get("incidents")).hasSize(2);
        assertThat(getJ("/api/v1/incidents/" + inc1, agent, 200).get("problems").get(0).get("problemNo").asString()).isEqualTo(p.get("problemNo").asString());

        patchJ("/api/v1/problems/" + id, agent, "{\"status\":\"RESOLVED\"}", 422); // OPEN cannot jump to RESOLVED
        patchJ("/api/v1/problems/" + id, agent, "{\"status\":\"INVESTIGATING\"}", 200);
        patchJ("/api/v1/problems/" + id, agent, "{\"status\":\"KNOWN_ERROR\"}", 422); // workaround missing
        JsonNode ke = patchJ("/api/v1/problems/" + id, agent, "{\"status\":\"KNOWN_ERROR\",\"workaround\":\"Restart the mail client\"}", 200);
        assertThat(ke.get("knownError").asBoolean()).isTrue();
        patchJ("/api/v1/problems/" + id, agent, "{\"status\":\"RESOLVED\"}", 422); // root cause missing
        JsonNode res = patchJ("/api/v1/problems/" + id, agent, "{\"status\":\"RESOLVED\",\"rootCause\":\"Expired certificate\"}", 200);
        assertThat(res.get("resolvedAt").asString()).isNotBlank();

        mvc.perform(delete("/api/v1/problems/" + id + "/incidents/" + inc2).header("Authorization", agent)).andExpect(status().isNoContent());
        mvc.perform(delete("/api/v1/problems/" + id + "/incidents/" + inc2).header("Authorization", agent)).andExpect(status().isNotFound());
        assertThat(getJ("/api/v1/problems/" + id, auditor, 200).get("incidentCount").asInt()).isEqualTo(1);

        List<String> snapshots = drain(Topics.INCIDENT_PROBLEMS).stream().filter(s -> s.startsWith(id + "\t")).toList();
        String latest = snapshots.get(snapshots.size() - 1);
        assertThat(latest).contains("\"eventType\":\"problem.snapshot\"").contains("\"status\":\"RESOLVED\"")
                .contains("\"knownError\":true").contains("\"incidentIds\":[" + inc1 + "]");
    }

    @Test
    void problemRbacTenantIsolationAndFilters() throws Exception {
        long inc = createIncident(eve);
        long id = postJ("/api/v1/problems", agent, "{\"title\":\"Filterable problem xyz\"}", 201).get("id").asLong();
        getJ("/api/v1/problems", eve, 403);
        postJ("/api/v1/problems", eve, "{\"title\":\"Employee problem\"}", 403);
        patchJ("/api/v1/problems/" + id, auditor, "{\"title\":\"Edited by auditor\"}", 403);
        getJ("/api/v1/problems/" + id, auditor, 200);
        getJ("/api/v1/problems/" + id, otherAdmin, 404);
        postJ("/api/v1/problems/" + id + "/incidents", agent, "{\"incidentIds\":[999999]}", 404);
        // an incident of another company cannot be linked, a problem of another company cannot be read
        long foreign = createIncident(otherEmployee, "{\"title\":\"Foreign incident\",\"description\":\"other company\"}");
        postJ("/api/v1/problems/" + id + "/incidents", agent, "{\"incidentIds\":[" + foreign + "]}", 404);
        postJ("/api/v1/problems", agent, "{\"title\":\"Wrong team\",\"ownerTeamId\":9}", 404);
        postJ("/api/v1/problems/" + id + "/incidents", agent, "{\"incidentIds\":[]}", 400);
        assertThat(getJ("/api/v1/problems?q=xyz&status=OPEN", agent, 200).get("total").asLong()).isEqualTo(1);
        assertThat(getJ("/api/v1/problems?knownError=true&q=xyz", agent, 200).get("total").asLong()).isZero();
        assertThat(getJ("/api/v1/problems", otherAdmin, 200).get("total").asLong()).isZero(); // other company sees none of ours
        assertThat(inc).isPositive();
    }

    // ---------- configuration ----------
    @Test
    void servicManagerTunesPrioritiesOthersCannot() throws Exception {
        putJ("/api/v1/admin/priorities/4", agent, "{\"responseMinutes\":480,\"resolutionMinutes\":5760}", 403);
        putJ("/api/v1/admin/priorities/4", manager, "{\"responseMinutes\":600,\"resolutionMinutes\":100}", 422);
        putJ("/api/v1/admin/priorities/9", manager, "{\"responseMinutes\":10,\"resolutionMinutes\":100}", 404);
        JsonNode p = putJ("/api/v1/admin/priorities/4", manager, "{\"responseMinutes\":480,\"resolutionMinutes\":5760}", 200);
        assertThat(p.get("name").asString()).isEqualTo("P4");
        assertThat(getJ("/api/v1/incidents/meta/priorities", eve, 200).get(3).get("resolutionMinutes").asInt()).isEqualTo(5760);
    }

    @Test
    void slaPolicyVersionsKeepHistory() throws Exception {
        getJ("/api/v1/admin/sla-policies", eve, 403);
        String body = "{\"name\":\"P1 gold\",\"priorityId\":1,\"serviceId\":2,\"businessHoursOnly\":true,\"responseTargetMinutes\":10,"
                + "\"resolutionTargetMinutes\":120,\"effectiveFrom\":\"2026-01-01\"}";
        JsonNode v1 = postJ("/api/v1/admin/sla-policies", manager, body, 201);
        assertThat(v1.get("version").asInt()).isEqualTo(1);
        postJ("/api/v1/admin/sla-policies", agent, body, 403);
        postJ("/api/v1/admin/sla-policies", manager, body.replace("2026-01-01", "2025-12-01"), 422); // not after the current start
        postJ("/api/v1/admin/sla-policies", manager, body.replace("\"resolutionTargetMinutes\":120", "\"resolutionTargetMinutes\":5"), 422);
        postJ("/api/v1/admin/sla-policies", manager, body.replace("\"serviceId\":2", "\"serviceId\":5"), 404);
        JsonNode v2 = postJ("/api/v1/admin/sla-policies", manager, body.replace("2026-01-01", "2026-06-01").replace("120", "90"), 201);
        assertThat(v2.get("version").asInt()).isEqualTo(2);
        JsonNode list = getJ("/api/v1/admin/sla-policies", auditor, 200);
        JsonNode first = list.valueStream().filter(x -> x.get("id").asLong() == v1.get("id").asLong()).findFirst().orElseThrow();
        assertThat(first.get("effectiveTo").asString()).isEqualTo("2026-05-31");
    }

    @Test
    void calendarsAreValidatedAndMappedToTheirTimezone() throws Exception {
        String hours = "[{\"weekday\":0,\"startTime\":\"09:00:00\",\"endTime\":\"18:00:00\"}]";
        assertThat(getJ("/api/v1/admin/calendars", eve, 200).size()).isGreaterThanOrEqualTo(3); // seeded UAE, UK, Sri Lanka
        postJ("/api/v1/admin/calendars", manager, "{\"name\":\"Moon\",\"timezone\":\"Mars/Base\",\"hours\":" + hours + "}", 422);
        postJ("/api/v1/admin/calendars", manager, "{\"name\":\"Dup\",\"timezone\":\"Asia/Tokyo\",\"hours\":[{\"weekday\":0,\"startTime\":\"09:00:00\",\"endTime\":\"18:00:00\"},{\"weekday\":0,\"startTime\":\"09:00:00\",\"endTime\":\"18:00:00\"}]}", 422);
        postJ("/api/v1/admin/calendars", manager, "{\"name\":\"Backwards\",\"timezone\":\"Asia/Tokyo\",\"hours\":[{\"weekday\":0,\"startTime\":\"18:00:00\",\"endTime\":\"09:00:00\"}]}", 422);
        postJ("/api/v1/admin/calendars", agent, "{\"name\":\"Tokyo\",\"timezone\":\"Asia/Tokyo\",\"hours\":" + hours + "}", 403);
        JsonNode c = postJ("/api/v1/admin/calendars", manager, "{\"name\":\"Tokyo Office\",\"timezone\":\"Asia/Tokyo\",\"hours\":" + hours
                + ",\"holidays\":[{\"holidayDate\":\"2026-01-01\",\"name\":\"New Year\"}]}", 201);
        assertThat(jdbc.queryForObject("SELECT calendar_id FROM timezone_calendars WHERE timezone='Asia/Tokyo'", Long.class)).isEqualTo(c.get("id").asLong());
        JsonNode u = putJ("/api/v1/admin/calendars/" + c.get("id").asLong(), manager, "{\"name\":\"Tokyo Office\",\"timezone\":\"Asia/Tokyo\",\"hours\":"
                + "[{\"weekday\":0,\"startTime\":\"08:00:00\",\"endTime\":\"12:00:00\"},{\"weekday\":1,\"startTime\":\"08:00:00\",\"endTime\":\"12:00:00\"}]}", 200);
        assertThat(u.get("hours")).hasSize(2);
        assertThat(u.get("holidays")).isEmpty();
        putJ("/api/v1/admin/calendars/999999", manager, "{\"name\":\"x1\",\"timezone\":\"Asia/Tokyo\",\"hours\":" + hours + "}", 404);
    }

    @Test
    void assignmentRulesRouteNewIncidents() throws Exception {
        getJ("/api/v1/admin/assignment-rules", eve, 403);
        postJ("/api/v1/admin/assignment-rules", agent, "{\"serviceId\":2,\"teamId\":2}", 403);
        postJ("/api/v1/admin/assignment-rules", manager, "{\"serviceId\":2,\"teamId\":9}", 404); // team of another company
        JsonNode rule = postJ("/api/v1/admin/assignment-rules", manager, "{\"serviceId\":2,\"priorityId\":null,\"teamId\":2,\"sortOrder\":1}", 201);
        long inc = createIncident(eve, "{\"title\":\"VPN is slow\",\"description\":\"routing test\",\"serviceId\":2}");
        assertThat(getJ("/api/v1/incidents/" + inc, agent, 200).get("assignedTeamId").asLong()).isEqualTo(2);
        // deactivated rules fall back to the service's owning team
        putJ("/api/v1/admin/assignment-rules/" + rule.get("id").asLong(), manager, "{\"serviceId\":2,\"teamId\":2,\"sortOrder\":1,\"active\":false}", 200);
        long inc2 = createIncident(eve, "{\"title\":\"VPN is slow again\",\"description\":\"routing test\",\"serviceId\":2}");
        assertThat(getJ("/api/v1/incidents/" + inc2, agent, 200).get("assignedTeamId").asLong()).isEqualTo(1);
        assertThat(getJ("/api/v1/admin/assignment-rules", lead, 200).size()).isGreaterThanOrEqualTo(1);
        putJ("/api/v1/admin/assignment-rules/999999", manager, "{\"teamId\":2}", 404);
    }

    @Test
    void escalationRulesAreValidated() throws Exception {
        assertThat(getJ("/api/v1/admin/escalation-rules", lead, 200).size()).isGreaterThanOrEqualTo(7); // seeded defaults
        getJ("/api/v1/admin/escalation-rules", agent, 403);
        postJ("/api/v1/admin/escalation-rules", manager, "{\"trigger\":\"RESPONSE_BREACH\",\"notifyRole\":\"WIZARD\"}", 422);
        postJ("/api/v1/admin/escalation-rules", manager, "{\"trigger\":\"SOMETHING\",\"notifyRole\":\"TEAM_LEAD\"}", 400);
        postJ("/api/v1/admin/escalation-rules", lead, "{\"trigger\":\"RESPONSE_BREACH\",\"notifyRole\":\"TEAM_LEAD\"}", 403);
        JsonNode r = postJ("/api/v1/admin/escalation-rules", manager, "{\"priorityId\":4,\"trigger\":\"RESPONSE_BREACH\",\"notifyRole\":\"SERVICE_MANAGER\"}", 201);
        assertThat(r.get("notifyAssignee").asBoolean()).isTrue();
        assertThat(r.get("active").asBoolean()).isTrue();
    }
}
