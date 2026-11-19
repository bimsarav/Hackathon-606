package com.esmhub.request.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.common.events.Topics;
import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class RequestServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaAdmin kafkaAdmin;

    // users: 1 Eve requester (manager 2), 2 Mark manager, 3 Sam service manager, 5 Tom technician in team 1, 6 Tina technician (no team),
    // 9 Oscar admin of another company
    String eve, mark, sam, tom, tina, oscar;
    long expensiveItem, cheapItem;

    @BeforeAll
    void seed() throws Exception {
        jdbc.update("INSERT INTO dir_users (user_id, company_id, first_name, last_name, email, employment_status, manager_id, roles) VALUES "
                + "(1,1,'Eve','Employee','eve@x','ACTIVE',2,'EMPLOYEE'),(2,1,'Mark','Manager','mark@x','ACTIVE',NULL,'EMPLOYEE'),"
                + "(3,1,'Sam','SvcMgr','sam@x','ACTIVE',NULL,'SERVICE_MANAGER'),(5,1,'Tom','Tech','tom@x','ACTIVE',NULL,'TECHNICIAN'),"
                + "(6,1,'Tina','Tech','tina@x','ACTIVE',NULL,'TECHNICIAN'),(9,2,'Oscar','Other','oscar@x','ACTIVE',NULL,'ADMIN')");
        jdbc.update("INSERT INTO dir_teams (team_id, company_id, name, support_level, manager_user_id, active) VALUES (1,1,'Service Desk',1,5,true)");
        jdbc.update("INSERT INTO dir_team_members (team_id, user_id) VALUES (1,5)");
        jdbc.update("INSERT INTO dir_services (service_id, company_id, name, owning_team_id, active) VALUES (1,1,'Hardware',1,true)");
        eve = TestJwt.bearer(1, 1, "EMPLOYEE");
        mark = TestJwt.bearer(2, 1, "EMPLOYEE");
        sam = TestJwt.bearer(3, 1, "SERVICE_MANAGER");
        tom = TestJwt.bearer(5, 1, List.of(1L), "TECHNICIAN");
        tina = TestJwt.bearer(6, 1, "TECHNICIAN");
        oscar = TestJwt.bearer(9, 2, "ADMIN");
        String steps = "\"steps\":[{\"stepOrder\":1,\"approverType\":\"MANAGER\",\"minCost\":0},"
                + "{\"stepOrder\":2,\"approverType\":\"ROLE\",\"approverRole\":\"SERVICE_MANAGER\",\"minCost\":1000}]";
        expensiveItem = createItem("Laptop request", 1200, steps);
        cheapItem = createItem("Mouse request", 20, steps);
    }

    long createItem(String name, int cost, String steps) throws Exception {
        var res = mvc.perform(post("/api/v1/catalogue").header("Authorization", sam).contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":1,\"name\":\"" + name + "\",\"baseCost\":" + cost + ",\"fulfilmentTeamId\":1," + steps + "}"))
                .andExpect(status().isCreated()).andReturn();
        return json.readTree(res.getResponse().getContentAsString()).get("itemId").asLong();
    }

    JsonNode create(String token, long itemId, String key) throws Exception {
        var b = post("/api/v1/requests").header("Authorization", token).contentType(MediaType.APPLICATION_JSON)
                .content("{\"itemId\":" + itemId + "}");
        if (key != null) b.header("Idempotency-Key", key);
        return json.readTree(mvc.perform(b).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString());
    }

    JsonNode get(String token, String path) throws Exception {
        return json.readTree(mvc.perform(get(path).header("Authorization", token)).andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    void decide(String token, long approvalId, String decision, int expected) throws Exception {
        mvc.perform(post("/api/v1/approvals/" + approvalId + "/decision").header("Authorization", token)
                .contentType(MediaType.APPLICATION_JSON).content("{\"decision\":\"" + decision + "\",\"comments\":\"c\"}"))
                .andExpect(status().is(expected));
    }

    void status(String token, long id, String to, int expected) throws Exception {
        mvc.perform(post("/api/v1/requests/" + id + "/status").header("Authorization", token)
                .contentType(MediaType.APPLICATION_JSON).content("{\"status\":\"" + to + "\"}")).andExpect(status().is(expected));
    }

    long pendingApprovalId(String token, long requestId) throws Exception {
        for (JsonNode a : get(token, "/api/v1/approvals")) if (a.get("requestId").asLong() == requestId) return a.get("approvalId").asLong();
        throw new AssertionError("no pending approval for request " + requestId);
    }

    @Test
    void catalogueWritesNeedServiceManagerOrAdmin() throws Exception {
        mvc.perform(post("/api/v1/catalogue").header("Authorization", eve).contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":1,\"name\":\"Nope item\"}")).andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/catalogue").header("Authorization", sam).contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":1,\"name\":\"Bad\",\"steps\":[{\"stepOrder\":1,\"approverType\":\"ROLE\"}]}")).andExpect(status().isUnprocessableContent());
        long id = createItem("Dock request", 100, "\"steps\":[]");
        mvc.perform(put("/api/v1/catalogue/" + id).header("Authorization", sam).contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":1,\"name\":\"Dock request v2\",\"baseCost\":120,\"steps\":[{\"stepOrder\":1,\"approverType\":\"MANAGER\"}]}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.steps.length()").value(1)).andExpect(jsonPath("$.name").value("Dock request v2"));
        mvc.perform(get("/api/v1/catalogue").header("Authorization", oscar)).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(0));
    }

    @Test
    void managerThenCostApprovalAndSecondDecisionConflict() throws Exception {
        JsonNode r = create(eve, expensiveItem, null);
        long id = r.get("requestId").asLong();
        assertThat(r.get("status").asString()).isEqualTo("PENDING_APPROVAL");
        assertThat(r.get("estimatedCost").asDouble()).isEqualTo(1200.0);
        assertThat(r.get("approvals").get(0).get("approverId").asLong()).isEqualTo(2);
        assertThat(get(eve, "/api/v1/approvals")).isEmpty();
        long a1 = pendingApprovalId(mark, id);
        decide(eve, a1, "APPROVED", 403);
        decide(sam, a1, "APPROVED", 403);
        decide(mark, a1, "APPROVED", 200);
        decide(mark, a1, "APPROVED", 409);
        assertThat(get(eve, "/api/v1/requests/" + id).get("status").asString()).isEqualTo("PENDING_APPROVAL");
        long a2 = pendingApprovalId(sam, id);
        decide(sam, a2, "APPROVED", 200);
        decide(sam, a2, "REJECTED", 409);
        JsonNode done = get(eve, "/api/v1/requests/" + id);
        assertThat(done.get("status").asString()).isEqualTo("APPROVED");
        assertThat(done.get("approvals").size()).isEqualTo(2);
        assertThat(done.get("approvedAt").isNull()).isFalse();
    }

    @Test
    void cheapRequestNeedsOnlyTheManager() throws Exception {
        long id = create(eve, cheapItem, null).get("requestId").asLong();
        decide(mark, pendingApprovalId(mark, id), "APPROVED", 200);
        assertThat(get(eve, "/api/v1/requests/" + id).get("status").asString()).isEqualTo("APPROVED");
        assertThat(get(sam, "/api/v1/approvals")).noneMatch(a -> a.get("requestId").asLong() == id);
    }

    @Test
    void rejectionEndsTheRequest() throws Exception {
        long id = create(eve, expensiveItem, null).get("requestId").asLong();
        decide(mark, pendingApprovalId(mark, id), "REJECTED", 200);
        assertThat(get(eve, "/api/v1/requests/" + id).get("status").asString()).isEqualTo("REJECTED");
        status(eve, id, "CANCELLED", 422);
    }

    @Test
    void requesterWhoHoldsTheApproverRoleStillCannotApproveOwnRequest() throws Exception {
        // Sam is the requester and a SERVICE_MANAGER; no line manager in the replica, so step 1 falls back to the role
        jdbc.update("INSERT INTO dir_users (user_id, company_id, first_name, last_name, email, employment_status, roles) VALUES (7,1,'Sue','Boss','sue@x','ACTIVE','SERVICE_MANAGER') ON CONFLICT DO NOTHING");
        long id = create(sam, cheapItem, null).get("requestId").asLong();
        JsonNode r = get(sam, "/api/v1/requests/" + id);
        assertThat(r.get("approvals").get(0).get("approverRole").asString()).isEqualTo("SERVICE_MANAGER");
        assertThat(get(sam, "/api/v1/approvals")).noneMatch(a -> a.get("requestId").asLong() == id);
        decide(sam, r.get("approvals").get(0).get("approvalId").asLong(), "APPROVED", 403);
        decide(TestJwt.bearer(7, 1, "SERVICE_MANAGER"), r.get("approvals").get(0).get("approvalId").asLong(), "APPROVED", 200);
    }

    @Test
    void fulfilmentIsRestrictedToTheFulfilmentTeam() throws Exception {
        long id = create(eve, cheapItem, null).get("requestId").asLong();
        status(tom, id, "IN_PROGRESS", 422);
        decide(mark, pendingApprovalId(mark, id), "APPROVED", 200);
        status(eve, id, "IN_PROGRESS", 403);
        status(tina, id, "IN_PROGRESS", 404);
        status(tom, id, "FULFILLED", 422);
        status(tom, id, "IN_PROGRESS", 200);
        assertThat(get(tom, "/api/v1/requests/" + id).get("canFulfil").asBoolean()).isTrue();
        assertThat(get(eve, "/api/v1/requests/" + id).get("canFulfil").asBoolean()).isFalse();
        assertThat(get(tom, "/api/v1/requests/" + id).get("assignedUserId").asLong()).isEqualTo(5);
        status(tom, id, "FULFILLED", 200);
        assertThat(get(eve, "/api/v1/requests/" + id).get("fulfilledAt").isNull()).isFalse();
        assertThat(get(tom, "/api/v1/requests?view=fulfilment&status=FULFILLED").get("items").size()).isGreaterThanOrEqualTo(1);
        assertThat(get(tina, "/api/v1/requests").get("total").asLong()).isZero();
    }

    @Test
    void requesterCanCancelAndPendingApprovalIsClosed() throws Exception {
        long id = create(eve, cheapItem, null).get("requestId").asLong();
        long approval = pendingApprovalId(mark, id);
        status(eve, id, "CANCELLED", 200);
        decide(mark, approval, "APPROVED", 409);
        assertThat(get(mark, "/api/v1/approvals")).noneMatch(a -> a.get("requestId").asLong() == id);
    }

    @Test
    void tenantIsolation() throws Exception {
        long id = create(eve, cheapItem, null).get("requestId").asLong();
        long approval = pendingApprovalId(mark, id);
        mvc.perform(get("/api/v1/requests/" + id).header("Authorization", oscar)).andExpect(status().isNotFound());
        assertThat(get(oscar, "/api/v1/requests").get("total").asLong()).isZero();
        decide(oscar, approval, "APPROVED", 404);
        mvc.perform(post("/api/v1/requests").header("Authorization", oscar).contentType(MediaType.APPLICATION_JSON)
                .content("{\"itemId\":" + cheapItem + "}")).andExpect(status().isNotFound());
        mvc.perform(put("/api/v1/catalogue/" + cheapItem).header("Authorization", oscar).contentType(MediaType.APPLICATION_JSON)
                .content("{\"serviceId\":1,\"name\":\"Hijack\"}")).andExpect(status().isForbidden());
    }

    @Test
    void listFiltersAndVisibility() throws Exception {
        long id = create(eve, cheapItem, null).get("requestId").asLong();
        assertThat(get(eve, "/api/v1/requests?view=mine&status=PENDING_APPROVAL&q=mouse").get("items")).anyMatch(i -> i.get("requestId").asLong() == id);
        assertThat(get(mark, "/api/v1/requests").get("total").asLong()).isZero();            // approver sees it only by id
        assertThat(get(mark, "/api/v1/requests/" + id).get("requestId").asLong()).isEqualTo(id);
        mvc.perform(get("/api/v1/requests/" + id).header("Authorization", tina)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/requests?size=500").header("Authorization", eve)).andExpect(status().isUnprocessableContent());
    }

    @Test
    void createIsIdempotent() throws Exception {
        long a = create(eve, cheapItem, "key-123").get("requestId").asLong();
        long b = create(eve, cheapItem, "key-123").get("requestId").asLong();
        assertThat(a).isEqualTo(b);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM service_requests WHERE requester_id=1", Long.class))
                .isEqualTo(jdbc.queryForObject("SELECT count(*) FROM service_requests WHERE requester_id=1 AND request_id <= " + a, Long.class)
                        + jdbc.queryForObject("SELECT count(*) FROM service_requests WHERE requester_id=1 AND request_id > " + a, Long.class));
        assertThat(jdbc.queryForObject("SELECT count(*) FROM idempotency_keys WHERE idem_key='key-123'", Long.class)).isEqualTo(1);
    }

    @Test
    void snapshotsAndNotificationEventsReachKafka() throws Exception {
        long id = create(eve, expensiveItem, null).get("requestId").asLong();
        decide(mark, pendingApprovalId(mark, id), "APPROVED", 200);
        Map<String, List<String>> snaps = drain(Topics.REQUEST_REQUESTS);
        JsonNode env = json.readTree(snaps.get(String.valueOf(id)).getLast());
        assertThat(env.get("eventType").asString()).isEqualTo("request.snapshot");
        assertThat(env.get("companyId").asLong()).isEqualTo(1);
        assertThat(env.get("payload").get("status").asString()).isEqualTo("PENDING_APPROVAL");
        assertThat(env.get("payload").get("requestNo").asString()).isEqualTo(String.format("REQ-%06d", id));
        assertThat(env.get("payload").get("requesterId").asLong()).isEqualTo(1);
        List<String> events = drain(Topics.REQUEST_EVENTS).getOrDefault(String.valueOf(id), List.of());
        List<JsonNode> nodes = new ArrayList<>();
        for (String e : events) nodes.add(json.readTree(e));
        assertThat(nodes).extracting(n -> n.get("eventType").asString())
                .contains("request.submitted", "request.approval_requested");
        var toSam = nodes.stream().filter(n -> n.get("eventType").asString().equals("request.approval_requested"))
                .filter(n -> n.get("payload").get("notification").get("notifyUserIds").get(0).asLong() == 3).count();
        assertThat(toSam).isEqualTo(1);
        var submitted = nodes.stream().filter(n -> n.get("eventType").asString().equals("request.submitted")).findFirst().orElseThrow();
        assertThat(submitted.get("payload").get("notification").get("notifyUserIds").get(0).asLong()).isEqualTo(5);
        assertThat(drain(Topics.AUDIT_EVENTS)).isNotEmpty();
    }

    /** Reads a topic from the beginning for up to ~10 s and returns all values per key. */
    Map<String, List<String>> drain(String topic) {
        Properties p = new Properties();
        p.put("bootstrap.servers", kafkaAdmin.getConfigurationProperties().get("bootstrap.servers"));
        p.put("group.id", "it-" + System.nanoTime());
        p.put("auto.offset.reset", "earliest");
        Map<String, List<String>> out = new HashMap<>();
        try (var c = new KafkaConsumer<>(p, new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            long end = System.currentTimeMillis() + 10_000;
            int emptyPolls = 0;
            while (System.currentTimeMillis() < end && emptyPolls < 3) {
                var recs = c.poll(Duration.ofMillis(1000));
                if (recs.isEmpty() && !out.isEmpty()) emptyPolls++;
                for (ConsumerRecord<String, String> r : recs) out.computeIfAbsent(r.key(), k -> new ArrayList<>()).add(r.value());
            }
        }
        return out;
    }
}
