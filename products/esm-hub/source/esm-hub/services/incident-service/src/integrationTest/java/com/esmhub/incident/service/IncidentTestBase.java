package com.esmhub.incident.service;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.esmhub.testsupport.TestJwt;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Shared fixtures: the directory replica is filled directly (it is normally fed from the directory.* topics). */
abstract class IncidentTestBase {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaAdmin kafkaAdmin;

    // company 1
    static final long ADMIN = 1, AGENT = 2, EVE = 3, EVAN = 4, AUDITOR = 8, TECH6 = 6, TECH7 = 7, LEAD = 20, MANAGER = 30;
    // company 2
    static final long OTHER_ADMIN = 90, OTHER_EMPLOYEE = 91;

    String admin = TestJwt.bearer(ADMIN, 1, "ADMIN");
    String agent = TestJwt.bearer(AGENT, 1, List.of(1L), "SERVICE_DESK_AGENT");
    String eve = TestJwt.bearer(EVE, 1, "EMPLOYEE");
    String evan = TestJwt.bearer(EVAN, 1, "EMPLOYEE");
    String auditor = TestJwt.bearer(AUDITOR, 1, "AUDITOR");
    String tech6 = TestJwt.bearer(TECH6, 1, List.of(1L), "TECHNICIAN");
    String tech7 = TestJwt.bearer(TECH7, 1, List.of(2L), "TECHNICIAN");
    String lead = TestJwt.bearer(LEAD, 1, List.of(1L), "TEAM_LEAD");
    String manager = TestJwt.bearer(MANAGER, 1, "SERVICE_MANAGER");
    String otherAdmin = TestJwt.bearer(OTHER_ADMIN, 2, "ADMIN");
    String otherEmployee = TestJwt.bearer(OTHER_EMPLOYEE, 2, "EMPLOYEE");

    void seedDirectory() {
        jdbc.update("INSERT INTO dir_offices (office_id, company_id, name, city, country, timezone) VALUES (1,1,'HQ','Abu Dhabi','UAE','Asia/Dubai') ON CONFLICT DO NOTHING");
        jdbc.update("INSERT INTO dir_teams (team_id, company_id, name, support_level, manager_user_id, active) VALUES "
                + "(1,1,'Service Desk',1,20,true),(2,1,'Network',2,NULL,true),(9,2,'Other Team',1,NULL,true) ON CONFLICT DO NOTHING");
        jdbc.update("INSERT INTO dir_team_members (team_id, user_id) VALUES (1,2),(1,6),(1,20),(2,7) ON CONFLICT DO NOTHING");
        jdbc.update("INSERT INTO dir_services (service_id, company_id, name, category_id, category_name, owning_team_id, active) VALUES "
                + "(1,1,'Email',1,'Workplace',1,true),(2,1,'Network',1,'Workplace',1,true),(3,1,'Retired',1,'Workplace',1,false),"
                + "(5,2,'Other service',1,'Workplace',9,true) ON CONFLICT DO NOTHING");
        user(ADMIN, 1, "Ada", "Admin", "ADMIN");
        user(AGENT, 1, "Omar", "Agent", "EMPLOYEE,SERVICE_DESK_AGENT");
        user(EVE, 1, "Eve", "Employee", "EMPLOYEE");
        user(EVAN, 1, "Evan", "Employee", "EMPLOYEE");
        user(AUDITOR, 1, "Audrey", "Auditor", "AUDITOR");
        user(TECH6, 1, "Tom", "Tech", "EMPLOYEE,TECHNICIAN");
        user(TECH7, 1, "Tia", "Tech", "EMPLOYEE,TECHNICIAN");
        user(LEAD, 1, "Lena", "Lead", "EMPLOYEE,TEAM_LEAD");
        user(MANAGER, 1, "Mo", "Manager", "EMPLOYEE,SERVICE_MANAGER");
        user(OTHER_ADMIN, 2, "Oscar", "Other", "ADMIN");
        user(OTHER_EMPLOYEE, 2, "Olga", "Other", "EMPLOYEE");
    }

    private void user(long id, long company, String first, String last, String roles) {
        jdbc.update("INSERT INTO dir_users (user_id, company_id, employee_no, first_name, last_name, email, office_id, employment_status, roles) "
                + "VALUES (?,?,?,?,?,?,1,'ACTIVE',?) ON CONFLICT DO NOTHING", id, company, "E" + id, first, last,
                first.toLowerCase() + "@example.test", roles);
    }

    // ---------- HTTP helpers ----------
    JsonNode call(org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder req, String token, int expected) throws Exception {
        var res = mvc.perform(req.header("Authorization", token)).andExpect(status().is(expected)).andReturn();
        String body = res.getResponse().getContentAsString();
        return body.isBlank() || body.startsWith("\"") ? null : json.readTree(body);
    }

    JsonNode postJ(String path, String token, String body, int expected) throws Exception {
        return call(post(path).contentType(MediaType.APPLICATION_JSON).content(body), token, expected);
    }

    JsonNode patchJ(String path, String token, String body, int expected) throws Exception {
        return call(patch(path).contentType(MediaType.APPLICATION_JSON).content(body), token, expected);
    }

    JsonNode putJ(String path, String token, String body, int expected) throws Exception {
        return call(put(path).contentType(MediaType.APPLICATION_JSON).content(body), token, expected);
    }

    JsonNode getJ(String path, String token, int expected) throws Exception { return call(get(path), token, expected); }

    long createIncident(String token, String json) throws Exception {
        return postJ("/api/v1/incidents", token, json, 201).get("id").asLong();
    }

    long createIncident(String token) throws Exception {
        return createIncident(token, "{\"title\":\"Email is down\",\"description\":\"Cannot send mail since morning\",\"serviceId\":1}");
    }

    void moveTo(long id, String token, String status, int expected) throws Exception {
        postJ("/api/v1/incidents/" + id + "/status", token, "{\"status\":\"" + status + "\"}", expected);
    }

    /** Takes an incident from NEW to IN_PROGRESS assigned to technician 6. */
    void assignToTech6(long id) throws Exception {
        postJ("/api/v1/incidents/" + id + "/assign", agent, "{\"teamId\":1,\"userId\":6}", 200);
        moveTo(id, tech6, "IN_PROGRESS", 200);
    }

    void resolve(long id) throws Exception {
        postJ("/api/v1/incidents/" + id + "/status", tech6, "{\"status\":\"RESOLVED\",\"resolutionCode\":\"FIXED\",\"resolutionNotes\":\"restarted\"}", 200);
    }

    /** Reads a topic from the beginning for up to ~10 s and returns all values. */
    List<String> drain(String topic) {
        Properties p = new Properties();
        p.put("bootstrap.servers", kafkaAdmin.getConfigurationProperties().get("bootstrap.servers"));
        p.put("group.id", "it-" + System.nanoTime());
        p.put("auto.offset.reset", "earliest");
        List<String> out = new ArrayList<>();
        try (var c = new KafkaConsumer<>(p, new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            long end = System.currentTimeMillis() + 10_000;
            int emptyPolls = 0;
            while (System.currentTimeMillis() < end && emptyPolls < 3) {
                var recs = c.poll(Duration.ofMillis(1000));
                if (recs.isEmpty() && !out.isEmpty()) emptyPolls++;
                for (ConsumerRecord<String, String> r : recs) out.add(r.key() + "\t" + r.value());
            }
        }
        return out;
    }
}
