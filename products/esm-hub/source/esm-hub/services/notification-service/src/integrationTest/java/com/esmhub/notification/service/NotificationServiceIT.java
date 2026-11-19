package com.esmhub.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.common.events.EventEnvelope;
import com.esmhub.common.events.Topics;
import com.esmhub.notification.service.notification.EmailDispatcher;
import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class NotificationServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaTemplate<String, String> kafka;
    @Autowired EmailDispatcher dispatcher;
    @MockitoBean JavaMailSender mail;

    String admin, eve, otherAdmin;

    @BeforeAll
    void seed() {
        String ins = "INSERT INTO dir_users (user_id, company_id, first_name, last_name, email, employment_status, roles) VALUES ";
        jdbc.update(ins + "(1,1,'Ada','Admin','ada@example.test','ACTIVE','ADMIN'),(2,1,'Eve','Employee','eve@example.test','ACTIVE','EMPLOYEE'),"
                + "(3,1,'Ian','Inactive','ian@example.test','INACTIVE','EMPLOYEE'),(9,2,'Oscar','Other','oscar@example.test','ACTIVE','ADMIN')");
        admin = TestJwt.bearer(1, 1, "ADMIN");
        eve = TestJwt.bearer(2, 1, "EMPLOYEE");
        otherAdmin = TestJwt.bearer(9, 2, "ADMIN");
    }

    UUID publish(UUID id, String ref, boolean email, Long... recipients) {
        DomainEvent ev = new DomainEvent("INCIDENT", "151", ref,
                new NotificationIntent(List.of(recipients), "Subject " + ref, "Message", "/incidents/151", email), Map.of());
        EventEnvelope env = new EventEnvelope(id, "incident.created", Instant.now(), 1L, 1L, null, "INCIDENT", "151", 1,
                json.valueToTree(ev));
        kafka.send(Topics.INCIDENT_EVENTS, "151", json.writeValueAsString(env));
        return id;
    }

    long count(String where) {
        return jdbc.queryForObject("SELECT count(*) FROM notifications WHERE " + where, Long.class);
    }

    @Test @Order(1)
    void eventCreatesOneInAppAndOneEmailPerEligibleRecipient() {
        UUID id = publish(UUID.randomUUID(), "INC-A", true, 2L, 3L, 9L, 1L, 2L);
        await().atMost(Duration.ofSeconds(60)).until(() -> count("reference = 'INC-A'") >= 4);
        assertThat(count("reference = 'INC-A'")).isEqualTo(4);
        assertThat(count("reference = 'INC-A' AND channel = 'IN_APP' AND delivery_status = 'DELIVERED'")).isEqualTo(2);
        assertThat(count("reference = 'INC-A' AND channel = 'EMAIL' AND delivery_status = 'PENDING'")).isEqualTo(2);
        assertThat(count("reference = 'INC-A' AND user_id IN (3, 9)")).isZero();

        // duplicate delivery of the same event, then a marker event: nothing new for INC-A
        publish(id, "INC-A", true, 2L, 3L, 9L, 1L, 2L);
        publish(UUID.randomUUID(), "INC-MARK", false, 2L);
        await().atMost(Duration.ofSeconds(60)).until(() -> count("reference = 'INC-MARK'") >= 1);
        assertThat(count("reference = 'INC-A'")).isEqualTo(4);
    }

    @Test @Order(2)
    void markReadIsDeniedForOtherUsersAndWorksForOwner() throws Exception {
        long evesInApp = jdbc.queryForObject("SELECT notification_id FROM notifications WHERE reference = 'INC-A' AND channel = 'IN_APP' AND user_id = 2", Long.class);
        mvc.perform(post("/api/v1/notifications/" + evesInApp + "/read").header("Authorization", admin)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/notifications/unread-count").header("Authorization", eve))
                .andExpect(status().isOk()).andExpect(jsonPath("$.unread").value(2));
        mvc.perform(get("/api/v1/notifications?unread=true").header("Authorization", eve))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(2)).andExpect(jsonPath("$.items[0].channel").value("IN_APP"));
        mvc.perform(post("/api/v1/notifications/" + evesInApp + "/read").header("Authorization", eve)).andExpect(status().isNoContent());
        mvc.perform(get("/api/v1/notifications/unread-count").header("Authorization", eve)).andExpect(jsonPath("$.unread").value(1));
        mvc.perform(post("/api/v1/notifications/read-all").header("Authorization", eve)).andExpect(status().isNoContent());
        mvc.perform(get("/api/v1/notifications/unread-count").header("Authorization", eve)).andExpect(jsonPath("$.unread").value(0));
        mvc.perform(get("/api/v1/notifications").header("Authorization", eve)).andExpect(jsonPath("$.total").value(2));
    }

    @Test @Order(3)
    void senderRetriesThenDeadThenAdminRetrySucceeds() throws Exception {
        doThrow(new IllegalStateException("smtp down")).when(mail).send(any(SimpleMailMessage.class));
        long id = jdbc.queryForObject("SELECT notification_id FROM notifications WHERE reference = 'INC-A' AND channel = 'EMAIL' AND user_id = 2", Long.class);
        jdbc.update("UPDATE notifications SET delivery_status = 'SENT' WHERE reference = 'INC-A' AND channel = 'EMAIL' AND user_id = 1");

        dispatcher.dispatchDue();
        assertThat(jdbc.queryForObject("SELECT delivery_status FROM notifications WHERE notification_id = ?", String.class, id)).isEqualTo("FAILED");
        dispatcher.dispatchDue(); // backoff not yet elapsed: untouched
        assertThat(jdbc.queryForObject("SELECT attempts FROM notifications WHERE notification_id = ?", Integer.class, id)).isEqualTo(1);
        for (int i = 0; i < 2; i++) {
            jdbc.update("UPDATE notifications SET next_attempt_at = now() WHERE notification_id = ?", id);
            dispatcher.dispatchDue();
        }
        assertThat(jdbc.queryForObject("SELECT delivery_status FROM notifications WHERE notification_id = ?", String.class, id)).isEqualTo("DEAD");

        mvc.perform(get("/api/v1/admin/notifications?status=DEAD").header("Authorization", admin))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(1))
                .andExpect(jsonPath("$.items[0].attempts").value(3)).andExpect(jsonPath("$.items[0].lastError").value(org.hamcrest.Matchers.containsString("smtp down")));
        mvc.perform(get("/api/v1/admin/notifications?status=DEAD").header("Authorization", eve)).andExpect(status().isForbidden());
        // tenant isolation: another company's admin sees nothing and cannot retry
        mvc.perform(get("/api/v1/admin/notifications?status=DEAD").header("Authorization", otherAdmin))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(0));
        mvc.perform(post("/api/v1/admin/notifications/" + id + "/retry").header("Authorization", otherAdmin)).andExpect(status().isNotFound());

        reset(mail);
        mvc.perform(post("/api/v1/admin/notifications/" + id + "/retry").header("Authorization", admin))
                .andExpect(status().isOk()).andExpect(jsonPath("$.deliveryStatus").value("PENDING")).andExpect(jsonPath("$.attempts").value(0));
        dispatcher.dispatchDue();
        assertThat(jdbc.queryForObject("SELECT delivery_status FROM notifications WHERE notification_id = ?", String.class, id)).isEqualTo("SENT");
        verify(mail, atLeastOnce()).send(any(SimpleMailMessage.class));
        // an in-app notification cannot be retried
        long inApp = jdbc.queryForObject("SELECT notification_id FROM notifications WHERE channel = 'IN_APP' LIMIT 1", Long.class);
        mvc.perform(post("/api/v1/admin/notifications/" + inApp + "/retry").header("Authorization", admin)).andExpect(status().isUnprocessableContent());
    }
}
