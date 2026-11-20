package com.esmhub.audit.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.esmhub.common.events.EventEnvelope;
import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class AuditServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaTemplate<String, String> kafka;

    String auditor, admin, employee, otherAuditor;

    @BeforeAll
    void tokens() {
        auditor = TestJwt.bearer(10, 1, "AUDITOR");
        admin = TestJwt.bearer(11, 1, "ADMIN");
        employee = TestJwt.bearer(12, 1, "EMPLOYEE");
        otherAuditor = TestJwt.bearer(30, 2, "AUDITOR");
    }

    UUID send(long company, String service, String entityType, String entityId, String action, long actor) throws Exception {
        UUID id = UUID.randomUUID();
        var payload = json.valueToTree(Map.of("service", service, "entityType", entityType, "entityId", entityId,
                "action", action, "oldValues", Map.of("status", "A"), "newValues", Map.of("status", "B"), "sourceIp", "10.1.2.3"));
        var env = new EventEnvelope(id, "audit." + action.toLowerCase(), Instant.now(), company, actor, "corr-" + id, entityType, entityId, 1, payload);
        kafka.send("audit.events", entityId, json.writeValueAsString(env)).get();
        return id;
    }

    void awaitRecords(String entityType, String entityId, int n) throws Exception {
        long end = System.currentTimeMillis() + 20_000;
        while (System.currentTimeMillis() < end) {
            Integer c = jdbc.queryForObject("SELECT count(*) FROM audit_records WHERE entity_type=? AND entity_id=?", Integer.class, entityType, entityId);
            if (c != null && c >= n) return;
            Thread.sleep(200);
        }
        throw new AssertionError("audit records not ingested for " + entityType + "/" + entityId);
    }

    JsonNode getJson(String token, String url, int status) throws Exception {
        var res = mvc.perform(get(url).header("Authorization", token)).andExpect(status().is(status)).andReturn().getResponse();
        String body = res.getContentAsString();
        return body.isBlank() || status >= 400 ? null : json.readTree(body);
    }

    @Test
    void eventsAreStoredOnceAndQueryable() throws Exception {
        UUID id = send(1, "asset-service", "ASSET", "IT-1", "ASSIGN", 77);
        kafka.send("audit.events", "IT-1", json.writeValueAsString(new EventEnvelope(id, "audit.assign", Instant.now(), 1L, 77L, "dup", "ASSET", "IT-1", 1,
                json.valueToTree(Map.of("service", "asset-service", "entityType", "ASSET", "entityId", "IT-1", "action", "ASSIGN"))))).get();
        awaitRecords("ASSET", "IT-1", 1);
        Thread.sleep(1500);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_records WHERE entity_id='IT-1'", Integer.class)).isEqualTo(1);

        JsonNode list = getJson(auditor, "/api/v1/audit?entityType=ASSET&entityId=IT-1", 200);
        assertThat(list.get("total").asInt()).isEqualTo(1);
        JsonNode r = list.get("items").get(0);
        assertThat(r.get("service").asString()).isEqualTo("asset-service");
        assertThat(r.get("actorUserId").asLong()).isEqualTo(77);
        assertThat(r.get("action").asString()).isEqualTo("ASSIGN");
        assertThat(r.get("newValues").get("status").asString()).isEqualTo("B");
        assertThat(r.get("sourceIp").asString()).isEqualTo("10.1.2.3");
        assertThat(getJson(admin, "/api/v1/audit?entityId=IT-1", 200).get("total").asInt()).isEqualTo(1);
    }

    @Test
    void filtersAndPaging() throws Exception {
        send(1, "kb", "ARTICLE", "F-1", "CREATE", 1);
        send(1, "kb", "ARTICLE", "F-1", "PUBLISH", 2);
        send(1, "kb", "ARTICLE", "F-1", "PUBLISH", 2);
        awaitRecords("ARTICLE", "F-1", 3);
        assertThat(getJson(auditor, "/api/v1/audit?entityId=F-1&action=PUBLISH", 200).get("total").asInt()).isEqualTo(2);
        assertThat(getJson(auditor, "/api/v1/audit?entityId=F-1&actorId=1", 200).get("total").asInt()).isEqualTo(1);
        assertThat(getJson(auditor, "/api/v1/audit?entityId=F-1&service=other", 200).get("total").asInt()).isZero();
        assertThat(getJson(auditor, "/api/v1/audit?entityId=F-1&from=2999-01-01T00:00:00Z", 200).get("total").asInt()).isZero();
        assertThat(getJson(auditor, "/api/v1/audit?entityId=F-1&to=2999-01-01T00:00:00Z", 200).get("total").asInt()).isEqualTo(3);
        JsonNode p = getJson(auditor, "/api/v1/audit?entityId=F-1&size=2&page=2", 200);
        assertThat(p.get("items").size()).isEqualTo(1);
        assertThat(p.get("total").asInt()).isEqualTo(3);
        getJson(auditor, "/api/v1/audit?size=500", 422);
    }

    @Test
    void rbacAndTenantIsolation() throws Exception {
        send(2, "kb", "ARTICLE", "T-1", "CREATE", 30);
        send(1, "kb", "ARTICLE", "T-1", "CREATE", 1);
        awaitRecords("ARTICLE", "T-1", 2);
        getJson(employee, "/api/v1/audit", 403);
        getJson(employee, "/api/v1/audit/export", 403);
        mvc.perform(get("/api/v1/audit")).andExpect(status().isUnauthorized());
        assertThat(getJson(auditor, "/api/v1/audit?entityId=T-1", 200).get("total").asInt()).isEqualTo(1);
        JsonNode other = getJson(otherAuditor, "/api/v1/audit?entityId=T-1", 200);
        assertThat(other.get("total").asInt()).isEqualTo(1);
        assertThat(other.get("items").get(0).get("actorUserId").asLong()).isEqualTo(30);
    }

    @Test
    void storeIsAppendOnly() throws Exception {
        send(1, "kb", "ARTICLE", "AO-1", "CREATE", 1);
        awaitRecords("ARTICLE", "AO-1", 1);
        assertThatThrownBy(() -> jdbc.update("UPDATE audit_records SET action='X' WHERE entity_id='AO-1'")).hasMessageContaining("append-only");
        assertThatThrownBy(() -> jdbc.update("DELETE FROM audit_records WHERE entity_id='AO-1'")).hasMessageContaining("append-only");
        assertThatThrownBy(() -> jdbc.execute("TRUNCATE audit_records")).hasMessageContaining("append-only");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_records WHERE entity_id='AO-1'", Integer.class)).isEqualTo(1);
    }

    @Test
    void exportIsCsvAndItselfAudited() throws Exception {
        send(1, "kb", "ARTICLE", "EX-1", "CREATE", 1);
        awaitRecords("ARTICLE", "EX-1", 1);
        var res = mvc.perform(get("/api/v1/audit/export?entityId=EX-1").header("Authorization", auditor))
                .andExpect(status().isOk()).andReturn().getResponse();
        assertThat(res.getContentType()).startsWith("text/csv");
        assertThat(res.getContentAsString()).contains("audit_id").contains("EX-1");
        awaitRecords("AUDIT", "0", 1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_records WHERE service='audit-service' AND action='EXPORT' AND actor_user_id=10", Integer.class))
                .isGreaterThanOrEqualTo(1);
    }
}
