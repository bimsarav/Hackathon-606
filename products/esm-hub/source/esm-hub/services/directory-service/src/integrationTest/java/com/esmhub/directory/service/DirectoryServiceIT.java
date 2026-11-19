package com.esmhub.directory.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.common.events.Topics;
import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.time.Duration;
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
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class DirectoryServiceIT {
    static final String PW = "Valid-Passw0rd";
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired PasswordEncoder encoder;
    @Autowired JsonMapper json;
    @Autowired org.springframework.kafka.core.KafkaAdmin kafkaAdmin;

    String admin, agent, employee;

    @BeforeAll
    void seed() {
        jdbc.update("INSERT INTO companies (company_id, name, code) VALUES (1,'Northstar','NSH'),(2,'Other','OTH')");
        jdbc.update("INSERT INTO offices (office_id, company_id, name, city, country, timezone) VALUES (1,1,'HQ','Abu Dhabi','UAE','Asia/Dubai')");
        jdbc.update("INSERT INTO teams (team_id, company_id, name, support_level) VALUES (1,1,'Service Desk',1),(2,2,'Other Team',1)");
        String h = encoder.encode(PW);
        jdbc.update("INSERT INTO users (user_id, company_id, employee_no, first_name, last_name, email, password_hash) VALUES "
                + "(1,1,'A1','Ada','Admin','admin@example.test',?),(2,1,'A2','Omar','Agent','agent@example.test',?),"
                + "(3,1,'A3','Eve','Employee','eve@example.test',?),(9,2,'O1','Oscar','Other','other@example.test',?)", h, h, h, h);
        jdbc.update("INSERT INTO user_roles SELECT 1, role_id FROM roles WHERE role_name='ADMIN'");
        jdbc.update("INSERT INTO user_roles SELECT 2, role_id FROM roles WHERE role_name='SERVICE_DESK_AGENT'");
        jdbc.update("INSERT INTO user_roles SELECT 3, role_id FROM roles WHERE role_name='EMPLOYEE'");
        jdbc.update("INSERT INTO user_roles SELECT 9, role_id FROM roles WHERE role_name='ADMIN'");
        jdbc.update("INSERT INTO team_members (team_id, user_id) VALUES (1,2)");
        jdbc.execute("SELECT setval(pg_get_serial_sequence('users','user_id'), 100)");
        jdbc.execute("SELECT setval(pg_get_serial_sequence('offices','office_id'), 100)");
        admin = TestJwt.bearer(1, 1, "ADMIN");
        agent = TestJwt.bearer(2, 1, List.of(1L), "SERVICE_DESK_AGENT");
        employee = TestJwt.bearer(3, 1, "EMPLOYEE");
    }

    String login(String email, String pw, int status) throws Exception {
        var res = mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"" + pw + "\"}"))
                .andExpect(status().is(status)).andReturn();
        return res.getResponse().getContentAsString();
    }

    @Test
    void loginIssuesTokenUsableForMe() throws Exception {
        String body = login("AGENT@example.test", PW, 200);
        String token = json.readTree(body).get("accessToken").asString();
        mvc.perform(get("/api/v1/auth/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roles[0]").value("SERVICE_DESK_AGENT"))
                .andExpect(jsonPath("$.teamIds[0]").value(1))
                .andExpect(jsonPath("$.companyId").value(1));
    }

    @Test
    void badCredentialsAndUnknownUserGetSame401() throws Exception {
        assertThat(login("eve@example.test", "Wrong-Passw0rd", 401)).contains("Invalid credentials");
        assertThat(login("nobody@example.test", PW, 401)).contains("Invalid credentials");
    }

    @Test
    void lockoutAfterFiveFailures() throws Exception {
        jdbc.update("INSERT INTO users (user_id, company_id, employee_no, first_name, last_name, email, password_hash) VALUES (50,1,'L1','Lock','Me','lock@example.test',?)", encoder.encode(PW));
        for (int i = 0; i < 5; i++) login("lock@example.test", "Wrong-Passw0rd", 401);
        login("lock@example.test", PW, 401);
        assertThat(jdbc.queryForObject("SELECT locked_until IS NOT NULL FROM users WHERE user_id=50", Boolean.class)).isTrue();
    }

    @Test
    void jwksIsPublicAndProtectedEndpointsNeedToken() throws Exception {
        mvc.perform(get("/.well-known/jwks.json")).andExpect(status().isOk()).andExpect(jsonPath("$.keys[0].kty").value("RSA"));
        mvc.perform(get("/api/v1/reference")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.requestId").exists());
        mvc.perform(get("/api/v1/reference").header("Authorization", "Bearer not-a-jwt")).andExpect(status().isUnauthorized());
    }

    @Test
    void referenceIsCompanyScoped() throws Exception {
        mvc.perform(get("/api/v1/reference").header("Authorization", employee)).andExpect(status().isOk())
                .andExpect(jsonPath("$.teams.length()").value(1))
                .andExpect(jsonPath("$.teams[0].name").value("Service Desk"))
                .andExpect(jsonPath("$.roles.length()").value(10));
    }

    @Test
    void directoryRequiresStaffRoleAndHidesOtherCompanies() throws Exception {
        mvc.perform(get("/api/v1/users").header("Authorization", employee)).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/users").param("q", "o").header("Authorization", agent)).andExpect(status().isOk())
                .andExpect(jsonPath("$.items[?(@.userId==9)]").isEmpty());
        mvc.perform(get("/api/v1/users/9").header("Authorization", agent)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/users/3").header("Authorization", employee)).andExpect(status().isOk());
    }

    @Test
    void adminCreatesUserWhoCanLogInAndPublishesSnapshot() throws Exception {
        mvc.perform(post("/api/v1/admin/users").header("Authorization", agent).contentType(MediaType.APPLICATION_JSON)
                .content("{\"employeeNo\":\"N1\",\"firstName\":\"N\",\"lastName\":\"U\",\"email\":\"n@example.test\",\"roles\":[\"EMPLOYEE\"]}"))
                .andExpect(status().isForbidden());
        String created = mvc.perform(post("/api/v1/admin/users").header("Authorization", admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"employeeNo\":\"N2\",\"firstName\":\"New\",\"lastName\":\"Hire\",\"email\":\"new.hire@example.test\","
                                + "\"officeId\":1,\"roles\":[\"TECHNICIAN\"],\"initialPassword\":\"" + PW + "\"}"))
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        long id = json.readTree(created).get("userId").asLong();
        login("new.hire@example.test", PW, 200);
        mvc.perform(post("/api/v1/admin/users").header("Authorization", admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"employeeNo\":\"N3\",\"firstName\":\"D\",\"lastName\":\"U\",\"email\":\"NEW.HIRE@example.test\",\"roles\":[\"EMPLOYEE\"]}"))
                .andExpect(status().isConflict());
        mvc.perform(patch("/api/v1/admin/users/" + id).header("Authorization", admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"roles\":[\"TECHNICIAN\",\"TEAM_LEAD\"],\"teamIds\":[1]}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.teamIds[0]").value(1));
        mvc.perform(patch("/api/v1/admin/users/1").header("Authorization", admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"roles\":[\"EMPLOYEE\"]}"))
                .andExpect(status().isUnprocessableContent());
        mvc.perform(patch("/api/v1/admin/users/9").header("Authorization", admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"employmentStatus\":\"INACTIVE\"}"))
                .andExpect(status().isNotFound());

        // The outbox relay publishes the user snapshot (with team membership) and audit events to Kafka
        Map<String, String> userTopic = drain(Topics.DIRECTORY_USERS);
        assertThat(userTopic.get(String.valueOf(id))).contains("TEAM_LEAD").contains("\"teamIds\":[1]");
        assertThat(String.join("\n", drain(Topics.AUDIT_EVENTS).values())).contains("ROLE_CHANGE");
    }

    @Test
    void adminRejectsInvalidTimezone() throws Exception {
        mvc.perform(post("/api/v1/admin/offices").header("Authorization", admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Moon\",\"city\":\"x\",\"country\":\"y\",\"timezone\":\"Mars/Base\"}"))
                .andExpect(status().isUnprocessableContent());
    }

    /** Reads a topic from the beginning for up to ~10 s and returns the last value per key. */
    Map<String, String> drain(String topic) {
        Properties p = new Properties();
        p.put("bootstrap.servers", kafkaAdmin.getConfigurationProperties().get("bootstrap.servers"));
        p.put("group.id", "it-" + System.nanoTime());
        p.put("auto.offset.reset", "earliest");
        Map<String, String> out = new java.util.HashMap<>();
        try (var c = new KafkaConsumer<>(p, new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of(topic));
            long end = System.currentTimeMillis() + 10_000;
            int emptyPolls = 0;
            while (System.currentTimeMillis() < end && emptyPolls < 3) {
                var recs = c.poll(Duration.ofMillis(1000));
                if (recs.isEmpty() && !out.isEmpty()) emptyPolls++;
                for (ConsumerRecord<String, String> r : recs) out.put(r.key(), r.value());
            }
        }
        return out;
    }
}
