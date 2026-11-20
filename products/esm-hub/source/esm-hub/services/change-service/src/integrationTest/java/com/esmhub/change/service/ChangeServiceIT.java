package com.esmhub.change.service;

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
class ChangeServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaAdmin kafkaAdmin;

    // users: 1 Tom technician in team 1 (author), 2 Cathy change manager, 3 Sam service manager, 4 Eve employee,
    // 5 Tina technician (no team), 6 Cleo second change manager, 9 Oscar admin of another company
    String tom, cathy, sam, eve, tina, cleo, oscar;

    @BeforeAll
    void seed() {
        jdbc.update("INSERT INTO dir_users (user_id, company_id, first_name, last_name, email, employment_status, manager_id, roles) VALUES "
                + "(1,1,'Tom','Tech','tom@x','ACTIVE',NULL,'TECHNICIAN'),(2,1,'Cathy','Change','cathy@x','ACTIVE',NULL,'CHANGE_MANAGER'),"
                + "(3,1,'Sam','SvcMgr','sam@x','ACTIVE',NULL,'SERVICE_MANAGER'),(4,1,'Eve','Employee','eve@x','ACTIVE',NULL,'EMPLOYEE'),"
                + "(5,1,'Tina','Tech','tina@x','ACTIVE',NULL,'TECHNICIAN'),(6,1,'Cleo','Change','cleo@x','ACTIVE',NULL,'CHANGE_MANAGER'),"
                + "(9,2,'Oscar','Other','oscar@x','ACTIVE',NULL,'ADMIN')");
        jdbc.update("INSERT INTO dir_teams (team_id, company_id, name, support_level, manager_user_id, active) VALUES (1,1,'Infra',2,1,true)");
        jdbc.update("INSERT INTO dir_team_members (team_id, user_id) VALUES (1,1)");
        tom = TestJwt.bearer(1, 1, List.of(1L), "TECHNICIAN");
        cathy = TestJwt.bearer(2, 1, "CHANGE_MANAGER");
        sam = TestJwt.bearer(3, 1, "SERVICE_MANAGER");
        eve = TestJwt.bearer(4, 1, "EMPLOYEE");
        tina = TestJwt.bearer(5, 1, "TECHNICIAN");
        cleo = TestJwt.bearer(6, 1, "CHANGE_MANAGER");
        oscar = TestJwt.bearer(9, 2, "ADMIN");
    }

    // ---------- helpers ----------
    String body(String title, String type, String risk, String start, String end) {
        return "{\"title\":\"" + title + "\",\"description\":\"desc\",\"changeType\":\"" + type + "\""
                + (risk == null ? "" : ",\"riskLevel\":\"" + risk + "\",\"impact\":\"LOW\"")
                + ",\"ownerTeamId\":1" + (start == null ? "" : ",\"plannedStart\":\"" + start + "\",\"plannedEnd\":\"" + end + "\"")
                + (risk == null ? "" : ",\"rollbackPlan\":\"revert\"") + "}";
    }

    JsonNode create(String token, String body) throws Exception {
        return json.readTree(mvc.perform(post("/api/v1/changes").header("Authorization", token)
                .contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString());
    }

    long full(String token, String title, String type, String risk, String start, String end) throws Exception {
        return create(token, body(title, type, risk, start, end)).get("changeId").asLong();
    }

    JsonNode getJson(String token, String path) throws Exception {
        return json.readTree(mvc.perform(get(path).header("Authorization", token)).andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    }

    JsonNode setStatus(String token, long id, String to, int expected) throws Exception {
        return json.readTree(mvc.perform(post("/api/v1/changes/" + id + "/status").header("Authorization", token)
                .contentType(MediaType.APPLICATION_JSON).content("{\"status\":\"" + to + "\"}")).andExpect(status().is(expected))
                .andReturn().getResponse().getContentAsString());
    }

    void decide(String token, long approvalId, String decision, int expected) throws Exception {
        mvc.perform(post("/api/v1/change-approvals/" + approvalId + "/decision").header("Authorization", token)
                .contentType(MediaType.APPLICATION_JSON).content("{\"decision\":\"" + decision + "\"}")).andExpect(status().is(expected));
    }

    long pendingId(String token, long changeId) throws Exception {
        for (JsonNode a : getJson(token, "/api/v1/change-approvals")) if (a.get("changeId").asLong() == changeId) return a.get("approvalId").asLong();
        throw new AssertionError("no pending approval for change " + changeId + " visible to this user");
    }

    long scheduled(String title, String type, String start, String end) throws Exception {
        long id = full(tom, title, type, "MEDIUM", start, end);
        setStatus(tom, id, "ASSESSMENT", 200);
        setStatus(tom, id, "APPROVAL", 200);
        decide(cathy, pendingId(cathy, id), "APPROVED", 200);
        return id;
    }

    String currentStatus(String token, long id) throws Exception { return getJson(token, "/api/v1/changes/" + id).get("status").asString(); }

    // ---------- tests ----------
    @Test
    void createValidatesAndEnforcesRoles() throws Exception {
        mvc.perform(post("/api/v1/changes").header("Authorization", eve).contentType(MediaType.APPLICATION_JSON)
                .content(body("Nope", "NORMAL", null, null, null))).andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/changes").header("Authorization", tom).contentType(MediaType.APPLICATION_JSON)
                .content(body("Bad window", "NORMAL", "LOW", "2030-01-01T12:00:00Z", "2030-01-01T10:00:00Z"))).andExpect(status().isUnprocessableContent());
        mvc.perform(post("/api/v1/changes").header("Authorization", tom).contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"x\",\"description\":\"d\",\"changeType\":\"NORMAL\",\"ownerTeamId\":99}")).andExpect(status().isUnprocessableContent());
        mvc.perform(post("/api/v1/changes").header("Authorization", tom).contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"x\",\"description\":\"d\",\"changeType\":\"WEIRD\"}")).andExpect(status().isBadRequest());
        JsonNode c = create(tom, body("Draft one", "NORMAL", null, null, null));
        assertThat(c.get("status").asString()).isEqualTo("DRAFT");
        assertThat(c.get("changeNo").asString()).isEqualTo(String.format("CHG-%06d", c.get("changeId").asLong()));
        assertThat(c.get("assessmentComplete").asBoolean()).isFalse();
        assertThat(c.get("canEdit").asBoolean()).isTrue();
    }

    @Test
    void incompleteAssessmentBlocksApproval() throws Exception {
        long id = full(tom, "Incomplete", "NORMAL", null, null, null);
        setStatus(tom, id, "ASSESSMENT", 200);
        JsonNode err = setStatus(tom, id, "APPROVAL", 422);
        assertThat(err.toString()).contains("riskLevel");
        assertThat(currentStatus(tom, id)).isEqualTo("ASSESSMENT");
    }

    @Test
    void standardChangeIsPreApproved() throws Exception {
        long id = full(tom, "Std patch", "STANDARD", "LOW", "2031-01-01T10:00:00Z", "2031-01-01T11:00:00Z");
        setStatus(tom, id, "ASSESSMENT", 200);
        JsonNode r = setStatus(tom, id, "APPROVAL", 200);
        assertThat(r.get("status").asString()).isEqualTo("SCHEDULED");
        assertThat(r.get("approvals")).isEmpty();
    }

    @Test
    void normalMediumNeedsChangeManagerAndLocksPlan() throws Exception {
        long id = full(tom, "Normal medium", "NORMAL", "MEDIUM", "2031-02-01T10:00:00Z", "2031-02-01T11:00:00Z");
        setStatus(tom, id, "ASSESSMENT", 200);
        setStatus(tom, id, "APPROVAL", 200);
        assertThat(getJson(sam, "/api/v1/change-approvals")).noneMatch(a -> a.get("changeId").asLong() == id);
        assertThat(getJson(tom, "/api/v1/change-approvals")).isEmpty();
        mvc.perform(put("/api/v1/changes/" + id).header("Authorization", tom).contentType(MediaType.APPLICATION_JSON)
                .content(body("Edited", "NORMAL", "LOW", null, null))).andExpect(status().isConflict());
        long ap = pendingId(cathy, id);
        decide(sam, ap, "APPROVED", 403);
        decide(cathy, ap, "APPROVED", 200);
        decide(cleo, ap, "APPROVED", 409);
        assertThat(currentStatus(tom, id)).isEqualTo("SCHEDULED");
        assertThat(getJson(tom, "/api/v1/changes/" + id).get("planLocked").asBoolean()).isTrue();
    }

    @Test
    void draftPlanCanBeEditedByAuthorOnly() throws Exception {
        long id = full(tom, "Editable", "NORMAL", null, null, null);
        mvc.perform(put("/api/v1/changes/" + id).header("Authorization", tom).contentType(MediaType.APPLICATION_JSON)
                .content(body("Edited title", "NORMAL", "HIGH", "2031-03-01T10:00:00Z", "2031-03-01T12:00:00Z")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.title").value("Edited title")).andExpect(jsonPath("$.assessmentComplete").value(true));
        mvc.perform(put("/api/v1/changes/" + id).header("Authorization", tina).contentType(MediaType.APPLICATION_JSON)
                .content(body("Hijack", "NORMAL", null, null, null))).andExpect(status().isNotFound());
        mvc.perform(put("/api/v1/changes/" + id).header("Authorization", eve).contentType(MediaType.APPLICATION_JSON)
                .content(body("Hijack", "NORMAL", null, null, null))).andExpect(status().isNotFound());
    }

    @Test
    void highRiskNormalChangeNeedsServiceManagerSecond() throws Exception {
        long id = full(tom, "Normal high", "NORMAL", "HIGH", "2031-04-01T10:00:00Z", "2031-04-01T11:00:00Z");
        setStatus(tom, id, "ASSESSMENT", 200);
        setStatus(tom, id, "APPROVAL", 200);
        assertThat(getJson(sam, "/api/v1/change-approvals")).noneMatch(a -> a.get("changeId").asLong() == id);
        decide(cathy, pendingId(cathy, id), "APPROVED", 200);
        assertThat(currentStatus(tom, id)).isEqualTo("APPROVAL");
        assertThat(getJson(cathy, "/api/v1/change-approvals")).noneMatch(a -> a.get("changeId").asLong() == id);
        decide(sam, pendingId(sam, id), "APPROVED", 200);
        JsonNode done = getJson(tom, "/api/v1/changes/" + id);
        assertThat(done.get("status").asString()).isEqualTo("SCHEDULED");
        assertThat(done.get("approvals").size()).isEqualTo(2);
    }

    @Test
    void rejectionEndsTheChangeAndRequesterCannotSelfApprove() throws Exception {
        long id = full(tom, "Rejected", "EMERGENCY", "LOW", "2031-05-01T10:00:00Z", "2031-05-01T11:00:00Z");
        setStatus(tom, id, "ASSESSMENT", 200);
        setStatus(tom, id, "APPROVAL", 200);
        decide(cathy, pendingId(cathy, id), "REJECTED", 200);
        assertThat(currentStatus(tom, id)).isEqualTo("REJECTED");
        setStatus(tom, id, "CANCELLED", 422);
        long own = full(cathy, "Own change", "EMERGENCY", "LOW", "2031-05-02T10:00:00Z", "2031-05-02T11:00:00Z");
        setStatus(cathy, own, "ASSESSMENT", 200);
        setStatus(cathy, own, "APPROVAL", 200);
        assertThat(getJson(cathy, "/api/v1/change-approvals")).noneMatch(a -> a.get("changeId").asLong() == own);
        decide(cathy, pendingId(cleo, own), "APPROVED", 403);   // segregation of duties
        decide(cleo, pendingId(cleo, own), "APPROVED", 200);
        assertThat(currentStatus(cathy, own)).isEqualTo("SCHEDULED");
    }

    @Test
    void implementAndCloseAreRoleRestricted() throws Exception {
        long id = scheduled("Lifecycle", "NORMAL", "2031-06-01T10:00:00Z", "2031-06-01T11:00:00Z");
        setStatus(tom, id, "IMPLEMENTED", 422);
        setStatus(tina, id, "IMPLEMENTING", 404);
        setStatus(eve, id, "IMPLEMENTING", 404);
        setStatus(tom, id, "IMPLEMENTING", 200);
        assertThat(getJson(tom, "/api/v1/changes/" + id).get("actualStart").isNull()).isFalse();
        setStatus(tom, id, "IMPLEMENTED", 200);
        assertThat(getJson(tom, "/api/v1/changes/" + id).get("actualEnd").isNull()).isFalse();
        setStatus(tom, id, "CLOSED", 403);
        setStatus(cathy, id, "CLOSED", 200);
        setStatus(cathy, id, "CANCELLED", 422);
        assertThat(currentStatus(cathy, id)).isEqualTo("CLOSED");
    }

    @Test
    void cancellingClosesOpenApprovals() throws Exception {
        long id = full(tom, "To cancel", "NORMAL", "MEDIUM", "2031-07-01T10:00:00Z", "2031-07-01T11:00:00Z");
        setStatus(tom, id, "ASSESSMENT", 200);
        setStatus(tom, id, "APPROVAL", 200);
        setStatus(tom, id, "CANCELLED", 200);
        assertThat(getJson(cathy, "/api/v1/change-approvals")).noneMatch(a -> a.get("changeId").asLong() == id);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM change_approvals WHERE change_id=" + id + " AND decision='PENDING'", Long.class)).isZero();
    }

    @Test
    void calendarShowsWindowsAndCollisions() throws Exception {
        long a = scheduled("Cal A", "NORMAL", "2040-01-01T10:00:00Z", "2040-01-01T12:00:00Z");
        long b = scheduled("Cal B", "EMERGENCY", "2040-01-01T11:00:00Z", "2040-01-01T13:00:00Z");
        long c = scheduled("Cal C", "NORMAL", "2040-01-02T10:00:00Z", "2040-01-02T11:00:00Z");
        JsonNode cal = getJson(cathy, "/api/v1/changes-calendar?from=2040-01-01T00:00:00Z&to=2040-01-03T00:00:00Z");
        assertThat(cal.size()).isEqualTo(3);
        JsonNode ea = null;
        JsonNode ec = null;
        for (JsonNode n : cal) {
            if (n.get("changeId").asLong() == a) ea = n;
            if (n.get("changeId").asLong() == c) ec = n;
        }
        assertThat(ea.get("collidesWith").get(0).asLong()).isEqualTo(b);
        assertThat(ec.get("collidesWith")).isEmpty();
        mvc.perform(get("/api/v1/changes-calendar").header("Authorization", eve)).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/changes-calendar?from=2040-01-03T00:00:00Z&to=2040-01-01T00:00:00Z").header("Authorization", cathy))
                .andExpect(status().isUnprocessableContent());
        assertThat(getJson(oscar, "/api/v1/changes-calendar?from=2040-01-01T00:00:00Z&to=2040-01-03T00:00:00Z")).isEmpty();
    }

    @Test
    void companyScopingAndVisibility() throws Exception {
        long id = full(tom, "Scoped change", "NORMAL", null, null, null);
        mvc.perform(get("/api/v1/changes/" + id).header("Authorization", oscar)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/changes/" + id).header("Authorization", eve)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/changes/" + id).header("Authorization", tina)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/changes/" + id).header("Authorization", cathy)).andExpect(status().isOk());
        assertThat(getJson(oscar, "/api/v1/changes").get("total").asLong()).isZero();
        assertThat(getJson(eve, "/api/v1/changes").get("total").asLong()).isZero();
        assertThat(getJson(tina, "/api/v1/changes").get("total").asLong()).isZero();
        mvc.perform(post("/api/v1/changes/" + id + "/status").header("Authorization", oscar).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"ASSESSMENT\"}")).andExpect(status().isNotFound());
    }

    @Test
    void listFiltersAndPaging() throws Exception {
        long id = full(tom, "Zebra firmware rollout", "EMERGENCY", "HIGH", null, null);
        assertThat(getJson(tom, "/api/v1/changes?view=mine&type=EMERGENCY&risk=HIGH&status=DRAFT&q=zebra").get("items"))
                .anyMatch(i -> i.get("changeId").asLong() == id);
        assertThat(getJson(cathy, "/api/v1/changes?q=zebra&type=NORMAL").get("total").asLong()).isZero();
        mvc.perform(get("/api/v1/changes?size=500").header("Authorization", cathy)).andExpect(status().isUnprocessableContent());
    }

    @Test
    void snapshotsAndNotificationEventsReachKafka() throws Exception {
        long id = full(tom, "Kafka change", "NORMAL", "HIGH", "2031-08-01T10:00:00Z", "2031-08-01T11:00:00Z");
        setStatus(tom, id, "ASSESSMENT", 200);
        setStatus(tom, id, "APPROVAL", 200);
        decide(cathy, pendingId(cathy, id), "APPROVED", 200);
        decide(sam, pendingId(sam, id), "APPROVED", 200);
        setStatus(tom, id, "IMPLEMENTING", 200);
        setStatus(tom, id, "FAILED", 200);
        Map<String, List<String>> snaps = drain(Topics.CHANGE_CHANGES);
        JsonNode env = json.readTree(snaps.get(String.valueOf(id)).getLast());
        assertThat(env.get("eventType").asString()).isEqualTo("change.snapshot");
        assertThat(env.get("companyId").asLong()).isEqualTo(1);
        assertThat(env.get("payload").get("status").asString()).isEqualTo("FAILED");
        assertThat(env.get("payload").get("changeNo").asString()).isEqualTo(String.format("CHG-%06d", id));
        assertThat(env.get("payload").get("riskLevel").asString()).isEqualTo("HIGH");
        List<JsonNode> nodes = new ArrayList<>();
        for (String e : drain(Topics.CHANGE_EVENTS).getOrDefault(String.valueOf(id), List.of())) nodes.add(json.readTree(e));
        assertThat(nodes).extracting(n -> n.get("eventType").asString())
                .contains("change.approval_requested", "change.approved", "change.failed");
        var failed = nodes.stream().filter(n -> n.get("eventType").asString().equals("change.failed")).findFirst().orElseThrow();
        List<Long> who = new ArrayList<>();
        failed.get("payload").get("notification").get("notifyUserIds").forEach(x -> who.add(x.asLong()));
        assertThat(who).contains(1L, 2L, 6L);   // requester Tom and both change managers
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
