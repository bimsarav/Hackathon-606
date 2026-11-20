package com.esmhub.incident.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.common.events.Topics;
import com.esmhub.testsupport.EsmContainers;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import tools.jackson.databind.JsonNode;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class IncidentLifecycleIT extends IncidentTestBase {
    @BeforeAll
    void seed() { seedDirectory(); }

    @Test
    void employeeLogsIncidentThatIsTriagedRoutedAndSlaTimed() throws Exception {
        JsonNode created = postJ("/api/v1/incidents", eve,
                "{\"title\":\"Email is down\",\"description\":\"Cannot send mail\",\"serviceId\":1,\"priorityId\":1}", 201);
        assertThat(created.get("priorityId").asInt()).isEqualTo(3); // employees cannot self-prioritise
        assertThat(created.get("status").asString()).isEqualTo("NEW");
        assertThat(created.get("ticketNo").asString()).matches("INC-\\d{6}");
        assertThat(created.get("assignedTeamId").asLong()).isEqualTo(1); // owning team of the service
        assertThat(created.get("requesterName").asString()).isEqualTo("Eve Employee");
        assertThat(created.get("dueAt").asString()).isNotBlank();
        assertThat(created.get("responseDueAt").asString()).isNotBlank();
        assertThat(created.get("allowedTransitions").toString()).contains("ASSIGNED").contains("CANCELLED");
        assertThat(created.get("events").get(0).get("eventType").asString()).isEqualTo("CREATED");
        getJ("/api/v1/incidents/" + created.get("id").asLong(), eve, 200);
    }

    @Test
    void fullLifecycleAssignWorkPauseResolveRateReopen() throws Exception {
        long id = createIncident(eve);
        JsonNode assigned = postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        assertThat(assigned.get("status").asString()).isEqualTo("ASSIGNED");
        assertThat(assigned.get("assigneeName").asString()).isEqualTo("Tom Tech");

        moveTo(id, tech6, "IN_PROGRESS", 200);
        JsonNode paused = postJ("/api/v1/incidents/" + id + "/status", tech6, "{\"status\":\"PENDING_USER\"}", 200);
        assertThat(paused.get("slaPaused").asBoolean()).isTrue();
        JsonNode resumed = postJ("/api/v1/incidents/" + id + "/status", tech6, "{\"status\":\"IN_PROGRESS\"}", 200);
        assertThat(resumed.get("slaPaused").asBoolean()).isFalse();
        assertThat(resumed.get("firstResponseAt").asString()).isNotBlank();

        postJ("/api/v1/incidents/" + id + "/status", tech6, "{\"status\":\"RESOLVED\"}", 422); // resolution code required
        resolve(id);
        postJ("/api/v1/incidents/" + id + "/satisfaction", eve, "{\"score\":5}", 200);
        postJ("/api/v1/incidents/" + id + "/satisfaction", agent, "{\"score\":5}", 403);

        JsonNode reopened = postJ("/api/v1/incidents/" + id + "/reopen", eve, "{\"reason\":\"It broke again\"}", 200);
        assertThat(reopened.get("status").asString()).isEqualTo("IN_PROGRESS");
        assertThat(reopened.get("reopenedCount").asInt()).isEqualTo(1);
        List<String> types = reopened.get("events").valueStream().map(e -> e.get("eventType").asString()).toList();
        assertThat(types).contains("CREATED", "ASSIGN", "SLA_PAUSE", "SLA_RESUME", "STATUS_CHANGE", "REOPEN");

        postJ("/api/v1/incidents/" + id + "/status", agent, "{\"status\":\"CANCELLED\"}", 422); // IN_PROGRESS cannot be cancelled
        resolve(id);
        moveTo(id, eve, "CLOSED", 200);
        postJ("/api/v1/incidents/" + id + "/reopen", eve, "{\"reason\":\"closed ones need a new ticket\"}", 422);
    }

    @Test
    void rbacDenialsAndTenantIsolation() throws Exception {
        long id = createIncident(eve);
        postJ("/api/v1/incidents/" + id + "/assign", eve, "{\"teamId\":1,\"userId\":6}", 403);
        postJ("/api/v1/incidents/" + id + "/status", eve, "{\"status\":\"IN_PROGRESS\"}", 403);
        patchJ("/api/v1/incidents/" + id, eve, "{\"priorityId\":1}", 403);
        postJ("/api/v1/incidents/" + id + "/worklogs", eve, "{\"minutesSpent\":10,\"workDescription\":\"nothing\"}", 403);
        mvc.perform(get("/api/v1/incidents/export").header("Authorization", eve)).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/incidents/" + id)).andExpect(status().isUnauthorized());
        // another employee, another technician (other team) and another company see nothing: 404, never 403
        getJ("/api/v1/incidents/" + id, evan, 404);
        getJ("/api/v1/incidents/" + id, tech7, 404);
        getJ("/api/v1/incidents/" + id, otherAdmin, 404);
        postJ("/api/v1/incidents/" + id + "/comments", otherEmployee, "{\"body\":\"hello\"}", 404);
        // an agent may not assign to a user outside the team, nor to a user without a resolver role
        postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":1,\"userId\":7}", 422);
        postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":1,\"userId\":3}", 422);
        postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":9,\"userId\":6}", 404);
        // a user of another company cannot be named as requester; employees cannot log for others
        postJ("/api/v1/incidents", agent, "{\"title\":\"For Olga\",\"description\":\"cross tenant\",\"requesterId\":91}", 404);
        postJ("/api/v1/incidents", eve, "{\"title\":\"For Evan\",\"description\":\"on behalf\",\"requesterId\":4}", 403);
        postJ("/api/v1/incidents", eve, "{\"title\":\"Retired svc\",\"description\":\"inactive service\",\"serviceId\":3}", 404);
        postJ("/api/v1/incidents", eve, "{\"title\":\"Foreign svc\",\"description\":\"other company\",\"serviceId\":5}", 404);
    }

    @Test
    void commentsInternalNotesAndWorklogs() throws Exception {
        long id = createIncident(eve);
        assignToTech6(id);
        postJ("/api/v1/incidents/" + id + "/comments", tech6, "{\"body\":\"secret diagnosis\",\"internal\":true}", 201);
        postJ("/api/v1/incidents/" + id + "/comments", tech6, "{\"body\":\"Please restart Outlook\"}", 201);
        postJ("/api/v1/incidents/" + id + "/comments", eve, "{\"body\":\"restarted, still failing\"}", 201);
        postJ("/api/v1/incidents/" + id + "/comments", eve, "{\"body\":\"my private note\",\"internal\":true}", 403);
        postJ("/api/v1/incidents/" + id + "/worklogs", tech6, "{\"minutesSpent\":45,\"workDescription\":\"diagnosis\"}", 201);

        JsonNode forEve = getJ("/api/v1/incidents/" + id, eve, 200);
        assertThat(forEve.get("comments").valueStream().map(c -> c.get("body").asString()).toList())
                .containsExactly("Please restart Outlook", "restarted, still failing");
        assertThat(forEve.has("worklogs") && forEve.get("worklogs").size() > 0).isFalse();
        JsonNode forAgent = getJ("/api/v1/incidents/" + id, agent, 200);
        assertThat(forAgent.get("comments")).hasSize(3);
        assertThat(forAgent.get("worklogs").get(0).get("minutesSpent").asInt()).isEqualTo(45);
        assertThat(forAgent.get("canWork").asBoolean()).isTrue();
    }

    @Test
    void listsAreScopedFilteredSortedAndPaged() throws Exception {
        long mine = createIncident(eve);
        long theirs = createIncident(evan);
        JsonNode eveList = getJ("/api/v1/incidents?size=200", eve, 200);
        List<Long> eveIds = eveList.get("items").valueStream().map(i -> i.get("id").asLong()).toList();
        assertThat(eveIds).contains(mine).doesNotContain(theirs);
        assertThat(eveList.get("items").get(0).has("comments")).isFalse(); // list rows carry no detail
        List<Long> agentIds = getJ("/api/v1/incidents?size=200&view=unassigned", agent, 200).get("items").valueStream()
                .map(i -> i.get("id").asLong()).toList();
        assertThat(agentIds).contains(mine, theirs);
        JsonNode page = getJ("/api/v1/incidents?size=1&page=1&sort=due&status=NEW&q=email", agent, 200);
        assertThat(page.get("items")).hasSize(1);
        assertThat(page.get("total").asLong()).isGreaterThanOrEqualTo(2);
        assertThat(page.get("page").asInt()).isEqualTo(1);
        getJ("/api/v1/incidents?size=500", agent, 422);
        getJ("/api/v1/incidents?view=nonsense", agent, 422);
        getJ("/api/v1/incidents?sort=nonsense", agent, 422);
        // a technician sees the queue of their team only
        assignToTech6(mine);
        List<Long> tech7Ids = getJ("/api/v1/incidents?size=200", tech7, 200).get("items").valueStream().map(i -> i.get("id").asLong()).toList();
        assertThat(tech7Ids).doesNotContain(mine);
        List<Long> queue = getJ("/api/v1/incidents?size=200&view=queue", tech6, 200).get("items").valueStream().map(i -> i.get("id").asLong()).toList();
        assertThat(queue).contains(mine);
        assertThat(getJ("/api/v1/incidents?size=200&view=assigned", tech6, 200).get("items").valueStream().map(i -> i.get("id").asLong()).toList())
                .contains(mine);
    }

    @Test
    void idempotencyKeyReturnsTheSameIncident() throws Exception {
        String body = "{\"title\":\"Double click\",\"description\":\"submitted twice\"}";
        long first = call(post("/api/v1/incidents").header("Idempotency-Key", "k-1").contentType(MediaType.APPLICATION_JSON).content(body), eve, 201).get("id").asLong();
        long second = call(post("/api/v1/incidents").header("Idempotency-Key", "k-1").contentType(MediaType.APPLICATION_JSON).content(body), eve, 201).get("id").asLong();
        assertThat(second).isEqualTo(first);
        long third = call(post("/api/v1/incidents").header("Idempotency-Key", "k-2").contentType(MediaType.APPLICATION_JSON).content(body), eve, 201).get("id").asLong();
        assertThat(third).isNotEqualTo(first);
    }

    @Test
    void validationErrorsAreProblemJson() throws Exception {
        postJ("/api/v1/incidents", eve, "{\"title\":\"x\",\"description\":\"too short title\"}", 400);
        postJ("/api/v1/incidents", eve, "{\"title\":\"Valid title\",\"description\":\"d\",\"channel\":\"CARRIER_PIGEON\"}", 400);
        postJ("/api/v1/incidents/999999/comments", agent, "{\"body\":\"nobody home\"}", 404);
    }

    @Test
    void metaPrioritiesAndExportForStaff() throws Exception {
        assertThat(getJ("/api/v1/incidents/meta/priorities", eve, 200)).hasSize(4);
        createIncident(eve);
        var res = mvc.perform(get("/api/v1/incidents/export?view=all").header("Authorization", auditor)).andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("text/csv")).andReturn();
        String csv = res.getResponse().getContentAsString();
        assertThat(csv).startsWith("ticket_no,title,status,priority").contains("Email is down");
    }

    @Test
    void kafkaRoundTripSnapshotsDomainEventsAndAudit() throws Exception {
        long id = createIncident(eve);
        assignToTech6(id);
        resolve(id);

        List<String> snapshots = drain(Topics.INCIDENT_INCIDENTS).stream().filter(s -> s.startsWith(id + "\t")).toList();
        assertThat(snapshots).isNotEmpty();
        String latest = snapshots.get(snapshots.size() - 1);
        assertThat(latest).contains("\"eventType\":\"incident.snapshot\"").contains("\"status\":\"RESOLVED\"").contains("\"closed\":true")
                .contains("\"assignedUserId\":6").contains("\"priority\":\"P3\"");

        String events = String.join("\n", drain(Topics.INCIDENT_EVENTS).stream().filter(s -> s.startsWith(id + "\t")).toList());
        assertThat(events).contains("incident.created").contains("incident.assigned").contains("incident.status_changed")
                .contains("\"reference\":\"INC-").contains("\"link\":\"/incidents/" + id + "\"").contains("\"notifyUserIds\":[3]");

        String audit = String.join("\n", drain(Topics.AUDIT_EVENTS));
        assertThat(audit).contains("\"entityId\":\"" + id + "\"").contains("\"action\":\"CREATE\"").contains("\"action\":\"ASSIGN\"");
    }
}
