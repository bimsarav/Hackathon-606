package com.esmhub.asset.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.time.Duration;
import java.time.LocalDate;
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
class AssetServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaAdmin kafkaAdmin;

    String manager, employee, employee14, auditor, otherManager, agent;

    @BeforeAll
    void seed() {
        jdbc.update("INSERT INTO dir_offices (office_id, company_id, name, city, country, timezone) VALUES "
                + "(1,1,'HQ','Abu Dhabi','UAE','Asia/Dubai'),(2,2,'Other HQ','London','UK','Europe/London')");
        jdbc.update("INSERT INTO dir_users (user_id, company_id, employee_no, first_name, last_name, email, employment_status, roles) VALUES "
                + "(10,1,'E10','Mia','Manager','m@x.test','ACTIVE','ASSET_MANAGER'),(11,1,'E11','Eve','Employee','e@x.test','ACTIVE','EMPLOYEE'),"
                + "(12,1,'E12','Ann','Auditor','a@x.test','ACTIVE','AUDITOR'),(13,1,'E13','Ian','Inactive','i@x.test','INACTIVE','EMPLOYEE'),"
                + "(14,1,'E14','Eli','Employee','e14@x.test','ACTIVE','EMPLOYEE'),(30,2,'E30','Oscar','Other','o@x.test','ACTIVE','ASSET_MANAGER')");
        manager = TestJwt.bearer(10, 1, "ASSET_MANAGER");
        employee = TestJwt.bearer(11, 1, "EMPLOYEE");
        employee14 = TestJwt.bearer(14, 1, "EMPLOYEE");
        auditor = TestJwt.bearer(12, 1, "AUDITOR");
        agent = TestJwt.bearer(15, 1, "SERVICE_DESK_AGENT");
        otherManager = TestJwt.bearer(30, 2, "ASSET_MANAGER");
    }

    JsonNode call(org.springframework.test.web.servlet.RequestBuilder rb, int status) throws Exception {
        var res = mvc.perform(rb).andExpect(status().is(status)).andReturn().getResponse();
        String body = res.getContentAsString();
        return body.isBlank() ? null : json.readTree(body);
    }

    JsonNode create(String token, String tag, String extra, int status) throws Exception {
        return call(post("/api/v1/assets").header("Authorization", token).contentType(MediaType.APPLICATION_JSON)
                .content("{\"assetTag\":\"" + tag + "\",\"assetType\":\"Laptop\"" + extra + "}"), status);
    }

    JsonNode post(String token, String path, String body, int status) throws Exception {
        return call(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post(path).header("Authorization", token)
                .contentType(MediaType.APPLICATION_JSON).content(body), status);
    }

    JsonNode get(String token, String path, int status) throws Exception {
        return call(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get(path).header("Authorization", token), status);
    }

    @Test
    void lifecycleWithHistory() throws Exception {
        String soon = LocalDate.now().plusDays(30).toString();
        JsonNode a = create(manager, "LC-1", ",\"manufacturer\":\"Dell\",\"model\":\"X1\",\"warrantyEnd\":\"" + soon + "\"", 201);
        long id = a.get("assetId").asLong();
        assertThat(a.get("status").asString()).isEqualTo("IN_STOCK");
        assertThat(a.get("warrantyState").asString()).isEqualTo("EXPIRING");

        assertThat(post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":11}", 200).get("status").asString()).isEqualTo("ASSIGNED");
        JsonNode second = post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":14}", 200);
        assertThat(second.get("assignedUserName").asString()).isEqualTo("Eli Employee");
        JsonNode hist = second.get("history");
        assertThat(hist).hasSize(2);
        assertThat(hist.get(0).get("userId").asLong()).isEqualTo(14);
        assertThat(hist.get(0).get("returnedAt").isNull()).isTrue();
        assertThat(hist.get(1).get("returnedAt").isNull()).isFalse();

        JsonNode repaired = post(manager, "/api/v1/assets/" + id + "/status", "{\"status\":\"REPAIR\"}", 200);
        assertThat(repaired.get("assignedUserId").isNull()).isTrue();
        assertThat(repaired.get("history").get(0).get("returnedAt").isNull()).isFalse();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM asset_assignments WHERE asset_id=? AND returned_at IS NULL", Long.class, id)).isZero();

        post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":11}", 422);
        post(manager, "/api/v1/assets/" + id + "/status", "{\"status\":\"ASSIGNED\"}", 422);
        post(manager, "/api/v1/assets/" + id + "/status", "{\"status\":\"RETIRED\"}", 200);
        post(manager, "/api/v1/assets/" + id + "/status", "{\"status\":\"IN_STOCK\"}", 422);

        assertThat(jdbc.queryForObject("SELECT count(*) FROM outbox_events WHERE topic='asset.events' AND event_type='asset.assigned' AND message_key=?",
                Long.class, String.valueOf(id))).isEqualTo(2);
        assertThat(jdbc.queryForList("SELECT event_type FROM outbox_events WHERE topic='audit.events' AND message_key=? ORDER BY id",
                String.class, String.valueOf(id))).containsExactly("audit.create", "audit.assign", "audit.assign", "audit.status_change", "audit.status_change");
        JsonNode event = json.readTree(jdbc.queryForObject("SELECT payload FROM outbox_events WHERE topic='asset.events' AND message_key=? ORDER BY id LIMIT 1",
                String.class, String.valueOf(id)));
        assertThat(event.get("payload").get("notification").get("notifyUserIds").get(0).asLong()).isEqualTo(11);
        assertThat(event.get("payload").get("notification").get("email").asBoolean()).isFalse();
    }

    @Test
    void snapshotsReachKafka() throws Exception {
        long id = create(manager, "KF-1", "", 201).get("assetId").asLong();
        post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":11}", 200);
        String key = String.valueOf(id);
        long end = System.currentTimeMillis() + 20_000;
        String last = null;
        while (System.currentTimeMillis() < end) {
            last = drain("asset.assets").get(key);
            if (last != null && last.contains("\"ASSIGNED\"")) break;
        }
        assertThat(last).contains("\"assignedUserId\":11").contains("\"assetTag\":\"KF-1\"");
    }

    @Test
    void rbac() throws Exception {
        create(employee, "RB-1", "", 403);
        create(auditor, "RB-1", "", 403);
        long id = create(manager, "RB-2", "", 201).get("assetId").asLong();
        post(employee, "/api/v1/assets/" + id + "/assign", "{\"userId\":11}", 403);
        post(agent, "/api/v1/assets/" + id + "/status", "{\"status\":\"LOST\"}", 403);
        call(patch("/api/v1/assets/" + id).header("Authorization", employee).contentType(MediaType.APPLICATION_JSON).content("{}"), 403);
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/api/v1/assets")).andExpect(status().isUnauthorized());
        get(auditor, "/api/v1/assets/" + id, 200);
        get(agent, "/api/v1/assets/" + id, 200);
    }

    @Test
    void employeeSeesOnlyOwnEquipment() throws Exception {
        long mine = create(manager, "OWN-1", "", 201).get("assetId").asLong();
        long other = create(manager, "OWN-2", "", 201).get("assetId").asLong();
        post(manager, "/api/v1/assets/" + mine + "/assign", "{\"userId\":11}", 200);
        post(manager, "/api/v1/assets/" + other + "/assign", "{\"userId\":14}", 200);
        JsonNode list = get(employee, "/api/v1/assets?size=200", 200);
        assertThat(list.get("items")).isNotEmpty();
        list.get("items").forEach(i -> assertThat(i.get("assignedUserId").asLong()).isEqualTo(11));
        get(employee, "/api/v1/assets/" + mine, 200);
        get(employee, "/api/v1/assets/" + other, 404);
        call(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/api/v1/assets/export").header("Authorization", employee), 403);
    }

    @Test
    void filters() throws Exception {
        LocalDate today = LocalDate.now();
        create(manager, "FLT-OLD", ",\"officeId\":1,\"warrantyEnd\":\"" + today.minusDays(5) + "\"", 201);
        create(manager, "FLT-SOON", ",\"warrantyEnd\":\"" + today.plusDays(10) + "\"", 201);
        create(manager, "FLT-LATER", ",\"officeId\":1,\"warrantyEnd\":\"" + today.plusDays(400) + "\"", 201);
        long phone = call(post("/api/v1/assets").header("Authorization", manager).contentType(MediaType.APPLICATION_JSON)
                .content("{\"assetTag\":\"FLT-PHONE\",\"assetType\":\"Phone\",\"model\":\"Pixelz\"}"), 201).get("assetId").asLong();
        post(manager, "/api/v1/assets/" + phone + "/assign", "{\"userId\":14}", 200);

        assertThat(get(manager, "/api/v1/assets?q=flt-", 200).get("total").asInt()).isEqualTo(4);
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&warranty=expired", 200))).containsExactly("FLT-OLD");
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&warranty=expiring", 200))).containsExactly("FLT-SOON");
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&type=Phone", 200))).containsExactly("FLT-PHONE");
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&status=ASSIGNED", 200))).containsExactly("FLT-PHONE");
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&assigneeId=14", 200))).containsExactly("FLT-PHONE");
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&officeId=1", 200))).containsExactly("FLT-LATER", "FLT-OLD");
        assertThat(tags(get(manager, "/api/v1/assets?q=pixelz", 200))).containsExactly("FLT-PHONE");
        assertThat(tags(get(manager, "/api/v1/assets?q=FLT-&status=IN_STOCK,LOST", 200))).hasSize(3);
        get(manager, "/api/v1/assets?warranty=bogus", 422);
        get(manager, "/api/v1/assets?size=500", 422);
    }

    List<String> tags(JsonNode page) {
        return page.get("items").valueStream().map(n -> n.get("assetTag").asString()).toList();
    }

    @Test
    void exportCsvIsRoleRestrictedAndAudited() throws Exception {
        create(manager, "EXP-1", ",\"model\":\"=HYPERLINK(1)\"", 201);
        for (String t : List.of(manager, auditor, TestJwt.bearer(16, 1, "SERVICE_MANAGER"), TestJwt.bearer(17, 1, "ADMIN"))) {
            String csv = mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/api/v1/assets/export?status=IN_STOCK")
                            .header("Authorization", t)).andExpect(status().isOk())
                    .andExpect(content().contentTypeCompatibleWith("text/csv")).andReturn().getResponse().getContentAsString();
            assertThat(csv).startsWith("asset_tag,type,manufacturer").contains("EXP-1").contains("'=HYPERLINK(1)");
        }
        call(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/api/v1/assets/export").header("Authorization", agent), 403);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM outbox_events WHERE topic='audit.events' AND event_type='audit.export'", Long.class)).isGreaterThanOrEqualTo(4);
    }

    @Test
    void tenantIsolation() throws Exception {
        long id = create(manager, "TEN-1", "", 201).get("assetId").asLong();
        get(otherManager, "/api/v1/assets/" + id, 404);
        post(otherManager, "/api/v1/assets/" + id + "/assign", "{\"userId\":30}", 404);
        post(otherManager, "/api/v1/assets/" + id + "/status", "{\"status\":\"LOST\"}", 404);
        call(patch("/api/v1/assets/" + id).header("Authorization", otherManager).contentType(MediaType.APPLICATION_JSON).content("{\"model\":\"x\"}"), 404);
        assertThat(get(otherManager, "/api/v1/assets?q=TEN-", 200).get("total").asInt()).isZero();
        // other tenant's office and users are not usable either
        create(otherManager, "TEN-2", ",\"officeId\":1", 404);
        post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":30}", 404);
        // the same tag may exist in another company
        create(otherManager, "TEN-1", ",\"officeId\":2", 201);
    }

    @Test
    void validationAndConflicts() throws Exception {
        create(manager, "VAL-1", ",\"serialNumber\":\"SN-1\"", 201);
        create(manager, "val-1", "", 409);
        create(manager, "VAL-2", ",\"serialNumber\":\"SN-1\"", 409);
        create(manager, "VAL-3", ",\"purchaseDate\":\"2026-02-01\",\"warrantyEnd\":\"2026-01-01\"", 422);
        create(manager, "X", "", 400);
        long id = create(manager, "VAL-4", "", 201).get("assetId").asLong();
        post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":13}", 422);
        post(manager, "/api/v1/assets/" + id + "/assign", "{\"userId\":999}", 404);
        post(manager, "/api/v1/assets/" + id + "/assign", "{}", 400);
        JsonNode patched = call(patch("/api/v1/assets/" + id).header("Authorization", manager).contentType(MediaType.APPLICATION_JSON)
                .content("{\"model\":\"New\",\"officeId\":1,\"purchaseCost\":199.50}"), 200);
        assertThat(patched.get("model").asString()).isEqualTo("New");
        assertThat(patched.get("officeId").asLong()).isEqualTo(1);
    }

    /** Reads a topic from the beginning for a few seconds and returns the last value per key. */
    Map<String, String> drain(String topic) {
        Properties p = new Properties();
        p.put("bootstrap.servers", kafkaAdmin.getConfigurationProperties().get("bootstrap.servers"));
        p.put("group.id", "it-" + System.nanoTime());
        p.put("auto.offset.reset", "earliest");
        Map<String, String> out = new HashMap<>();
        try (var c = new KafkaConsumer<>(p, new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            long end = System.currentTimeMillis() + 4_000;
            while (System.currentTimeMillis() < end) {
                for (ConsumerRecord<String, String> r : c.poll(Duration.ofMillis(500))) out.put(r.key(), r.value());
            }
        }
        return out;
    }
}
