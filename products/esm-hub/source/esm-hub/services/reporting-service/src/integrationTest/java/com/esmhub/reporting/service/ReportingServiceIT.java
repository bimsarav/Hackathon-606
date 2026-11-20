package com.esmhub.reporting.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.common.contracts.DomainContracts.*;
import com.esmhub.common.events.EventEnvelope;
import com.esmhub.common.events.Topics;
import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
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
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class ReportingServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaTemplate<String, String> kafka;

    String admin, otherAdmin, employee;
    final Instant now = Instant.now();

    @BeforeAll
    void seedDirectoryAndProjections() {
        jdbc.update("INSERT INTO dir_offices (office_id, company_id, name, timezone) VALUES (30, 1, 'Colombo', 'UTC')");
        jdbc.update("INSERT INTO dir_teams (team_id, company_id, name, support_level, active) VALUES (10, 1, 'Network', 1, true)");
        jdbc.update("INSERT INTO dir_services (service_id, company_id, name, active) VALUES (20, 1, 'Email', true)");
        jdbc.update("INSERT INTO dir_users (user_id, company_id, first_name, last_name, email, office_id, employment_status, roles) VALUES "
                + "(1, 1, 'Ada', 'Admin', 'ada@example.test', 30, 'ACTIVE', 'ADMIN'), (2, 1, 'Eve', 'Employee', 'eve@example.test', 30, 'ACTIVE', 'EMPLOYEE')");
        admin = TestJwt.bearer(1, 1, "ADMIN");
        employee = TestJwt.bearer(2, 1, "EMPLOYEE");
        otherAdmin = TestJwt.bearer(9, 2, "ADMIN");

        incident(1, 1, "P1", 10L, null, 5 * 24, 10, 120, false, 0, 4, true, 0);
        incident(2, 1, "P1", null, null, 4 * 24, 30, 300, true, 1, 2, true, 0);
        incident(3, 1, "P2", 10L, null, 40 * 24, -1, -1, true, 0, null, false, 0);
        incident(4, 1, "P3", 10L, 2L, 2, -1, -1, false, 0, null, false, 45);
        incident(5, 2, "P1", null, null, 24, -1, -1, false, 0, null, false, 0);

        send(Topics.REQUEST_REQUESTS, "1", "request.snapshot", new RequestSnapshot(1, 1, "REQ-1", "Laptop", "FULFILLED", 2, 20L, null,
                new BigDecimal("100.00"), 10L, now.minus(3, ChronoUnit.DAYS), now.minus(3, ChronoUnit.DAYS).plus(2, ChronoUnit.HOURS),
                now.minus(3, ChronoUnit.DAYS).plus(10, ChronoUnit.HOURS)));
        send(Topics.REQUEST_REQUESTS, "2", "request.snapshot", new RequestSnapshot(2, 1, "REQ-2", "Phone", "REJECTED", 2, 20L, null,
                new BigDecimal("50.00"), 10L, now.minus(2, ChronoUnit.DAYS), null, null));
        send(Topics.REQUEST_REQUESTS, "3", "request.snapshot", new RequestSnapshot(3, 1, "REQ-3", "Mouse", "SUBMITTED", 2, 20L, null,
                new BigDecimal("25.00"), 10L, now.minus(1, ChronoUnit.DAYS), null, null));
        send(Topics.CHANGE_CHANGES, "1", "change.snapshot", change(1, "IMPLEMENTED"));
        send(Topics.CHANGE_CHANGES, "2", "change.snapshot", change(2, "FAILED"));
        LocalDate today = LocalDate.now();
        send(Topics.ASSET_ASSETS, "1", "asset.snapshot", new AssetSnapshot(1, 1, "A-1", "LAPTOP", "ASSIGNED", 2L, 30L, today.minusDays(100), today.plusDays(400), new BigDecimal("1000.00")));
        send(Topics.ASSET_ASSETS, "2", "asset.snapshot", new AssetSnapshot(2, 1, "A-2", "LAPTOP", "ASSIGNED", 2L, 30L, today.minusDays(900), today.minusDays(5), new BigDecimal("500.00")));
        send(Topics.INCIDENT_PROBLEMS, "1", "problem.snapshot", new ProblemSnapshot(1, 1, "PRB-1", "Mail outages", "OPEN", true, 10L, now, null, List.of(1L, 3L)));
        // a record that is created and then tombstoned must not appear
        incident(6, 1, "P4", null, null, 3, -1, -1, false, 0, null, false, 0);
    }

    void incident(long id, long company, String priority, Long team, Long user, int ageHours, int respMin, int resolveMin,
                  boolean breached, int reopened, Integer csat, boolean closed, int worklog) {
        Instant created = now.minus(ageHours, ChronoUnit.HOURS);
        boolean resolved = resolveMin >= 0;
        send(Topics.INCIDENT_INCIDENTS, String.valueOf(id), "incident.snapshot", new IncidentSnapshot(id, company, "INC-" + id, "Title " + id,
                closed ? "CLOSED" : "NEW", closed, priority, 20L, "PORTAL", 2, team, user, created,
                respMin >= 0 ? created.plus(respMin, ChronoUnit.MINUTES) : null, resolved ? created.plus(resolveMin, ChronoUnit.MINUTES) : null,
                closed ? created.plus(resolveMin, ChronoUnit.MINUTES) : null, null, null, false, breached, false, reopened, csat, worklog));
    }


    ChangeSnapshot change(long id, String status) {
        return new ChangeSnapshot(id, 1, "CHG-" + id, "Change " + id, "NORMAL", status, "HIGH", "MEDIUM", 10L, 2L, null, null, null, null, now);
    }

    void send(String topic, String key, String type, Object payload) {
        EventEnvelope env = new EventEnvelope(UUID.randomUUID(), type, Instant.now(), 1L, null, null, "X", key, 1, json.valueToTree(payload));
        kafka.send(topic, key, json.writeValueAsString(env));
    }

    long count(String table) {
        return jdbc.queryForObject("SELECT count(*) FROM " + table, Long.class);
    }

    @Test @Order(1)
    void snapshotsAreProjectedAndTombstonesDelete() {
        await().atMost(Duration.ofSeconds(90)).until(() -> count("rpt_incidents") == 6 && count("rpt_requests") == 3
                && count("rpt_changes") == 2 && count("rpt_assets") == 2 && count("rpt_problem_incidents") == 2);
        kafka.send(Topics.INCIDENT_INCIDENTS, "6", null);
        await().atMost(Duration.ofSeconds(60)).until(() -> count("rpt_incidents") == 5);
        // an updated snapshot replaces the row (idempotent upsert)
        incident(4, 1, "P3", 10L, 2L, 2, -1, -1, false, 0, null, false, 45);
        send(Topics.INCIDENT_PROBLEMS, "1", "problem.snapshot", new ProblemSnapshot(1, 1, "PRB-1", "Mail outages", "OPEN", true, 10L, now, null, List.of(1L, 3L)));
        assertThat(count("rpt_incidents")).isEqualTo(5);
        assertThat(count("rpt_problems")).isEqualTo(1);
    }

    @Test @Order(2)
    void summaryUsesResolvedAsDenominatorAndIsCompanyScoped() throws Exception {
        mvc.perform(get("/api/v1/reports/summary").header("Authorization", admin)).andExpect(status().isOk())
                .andExpect(jsonPath("$.created").value(4)).andExpect(jsonPath("$.resolved").value(2))
                .andExpect(jsonPath("$.resolutionSlaPct").value(50.0)).andExpect(jsonPath("$.responseSlaPct").value(100.0))
                .andExpect(jsonPath("$.reopenRatePct").value(50.0)).andExpect(jsonPath("$.avgCsat").value(3.0))
                .andExpect(jsonPath("$.openBacklog").value(2)).andExpect(jsonPath("$.unassigned").value(1))
                .andExpect(jsonPath("$.openBreached").value(1)).andExpect(jsonPath("$.openRequests").value(1));
        mvc.perform(get("/api/v1/reports/summary").header("Authorization", otherAdmin)).andExpect(status().isOk())
                .andExpect(jsonPath("$.created").value(1)).andExpect(jsonPath("$.openRequests").value(0));
        // narrow window excludes the 40 day old incident
        String since = LocalDate.now().minusDays(10).toString();
        mvc.perform(get("/api/v1/reports/summary?since=" + since).header("Authorization", admin))
                .andExpect(jsonPath("$.created").value(3));
    }

    @Test @Order(3)
    void incidentVolumeByDimension() throws Exception {
        mvc.perform(get("/api/v1/reports/incident-volume?by=priority").header("Authorization", admin)).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3)).andExpect(jsonPath("$[0].key").value("P1"))
                .andExpect(jsonPath("$[0].count").value(2)).andExpect(jsonPath("$[0].breached").value(1));
        mvc.perform(get("/api/v1/reports/incident-volume?by=team").header("Authorization", admin))
                .andExpect(jsonPath("$[0].key").value("Network")).andExpect(jsonPath("$[0].count").value(3))
                .andExpect(jsonPath("$[1].key").value("Unassigned"));
        mvc.perform(get("/api/v1/reports/incident-volume?by=office").header("Authorization", admin))
                .andExpect(jsonPath("$[0].key").value("Colombo")).andExpect(jsonPath("$[0].count").value(4));
        mvc.perform(get("/api/v1/reports/incident-volume?by=service").header("Authorization", admin))
                .andExpect(jsonPath("$[0].key").value("Email"));
        mvc.perform(get("/api/v1/reports/incident-volume?by=month").header("Authorization", admin)).andExpect(status().isOk());
        mvc.perform(get("/api/v1/reports/incident-volume?by=week").header("Authorization", admin)).andExpect(status().isOk());
        mvc.perform(get("/api/v1/reports/incident-volume?by=bogus").header("Authorization", admin)).andExpect(status().isUnprocessableContent());
    }

    @Test @Order(4)
    void slaBacklogAndWorkload() throws Exception {
        mvc.perform(get("/api/v1/reports/sla-compliance").header("Authorization", admin)).andExpect(status().isOk())
                .andExpect(jsonPath("$[0].priority").value("P1")).andExpect(jsonPath("$[0].resolutionMetPct").value(50.0))
                .andExpect(jsonPath("$[0].responseMetPct").value(100.0));
        mvc.perform(get("/api/v1/reports/backlog-ageing").header("Authorization", admin))
                .andExpect(jsonPath("$.length()").value(2)).andExpect(jsonPath("$[0].bucket").value("0-1d"))
                .andExpect(jsonPath("$[1].bucket").value("30d+")).andExpect(jsonPath("$[1].priority").value("P2"));
        mvc.perform(get("/api/v1/reports/workload").header("Authorization", admin))
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[?(@.assignee == 'Eve Employee')].effortMinutes").value(45))
                .andExpect(jsonPath("$[?(@.assignee == 'Unassigned')].breached").value(1));
    }

    @Test @Order(5)
    void assetsRequestsChangesProblems() throws Exception {
        mvc.perform(get("/api/v1/reports/assets").header("Authorization", admin))
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[?(@.warranty == 'EXPIRED')].value").value(500.0))
                .andExpect(jsonPath("$[?(@.warranty == 'ACTIVE')].count").value(1));
        mvc.perform(get("/api/v1/reports/requests").header("Authorization", admin))
                .andExpect(jsonPath("$[0].service").value("Email")).andExpect(jsonPath("$[0].requests").value(3))
                .andExpect(jsonPath("$[0].fulfilled").value(1)).andExpect(jsonPath("$[0].rejected").value(1))
                .andExpect(jsonPath("$[0].totalCost").value(175.0)).andExpect(jsonPath("$[0].avgFulfilmentHours").value(10.0));
        mvc.perform(get("/api/v1/reports/changes").header("Authorization", admin))
                .andExpect(jsonPath("$[0].changeType").value("NORMAL")).andExpect(jsonPath("$[0].changes").value(2))
                .andExpect(jsonPath("$[0].failed").value(1)).andExpect(jsonPath("$[0].failureRatePct").value(50.0));
        mvc.perform(get("/api/v1/reports/problems").header("Authorization", admin))
                .andExpect(jsonPath("$.coverage.incidents").value(4)).andExpect(jsonPath("$.coverage.linked").value(2))
                .andExpect(jsonPath("$.coverage.coveragePct").value(50.0)).andExpect(jsonPath("$.byStatus[0].knownErrors").value(1))
                .andExpect(jsonPath("$.topServices90d[0].service").value("Email"));
    }

    @Test @Order(6)
    void rbacTenantAndExports() throws Exception {
        mvc.perform(get("/api/v1/reports/summary").header("Authorization", employee)).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/reports/summary")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/reports/summary?since=2026-03-01&until=2026-02-01").header("Authorization", admin))
                .andExpect(status().isUnprocessableContent());
        mvc.perform(get("/api/v1/reports/assets").header("Authorization", otherAdmin)).andExpect(jsonPath("$.length()").value(0));

        String csv = mvc.perform(get("/api/v1/reports/incident-volume/export?by=priority").header("Authorization", admin))
                .andExpect(status().isOk()).andExpect(header().string("Content-Disposition", org.hamcrest.Matchers.containsString("incident-volume.csv")))
                .andReturn().getResponse().getContentAsString();
        assertThat(csv).contains("key").contains("P1");
        mvc.perform(get("/api/v1/reports/problems/export").header("Authorization", admin)).andExpect(status().isOk());
        mvc.perform(get("/api/v1/reports/nope/export").header("Authorization", admin)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/reports/workload/export").header("Authorization", employee)).andExpect(status().isForbidden());
        // empty result still yields a CSV with a placeholder header
        String empty = mvc.perform(get("/api/v1/reports/assets/export").header("Authorization", otherAdmin))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(empty).contains("no_data");
    }
}
