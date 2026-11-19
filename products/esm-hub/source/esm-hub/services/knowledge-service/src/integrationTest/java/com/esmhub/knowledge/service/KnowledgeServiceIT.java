package com.esmhub.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.esmhub.testsupport.EsmContainers;
import com.esmhub.testsupport.TestJwt;
import java.time.Duration;
import java.util.HashSet;
import java.util.List;
import java.util.Properties;
import java.util.Set;
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
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(EsmContainers.class)
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class KnowledgeServiceIT {
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired JsonMapper json;
    @Autowired KafkaAdmin kafkaAdmin;

    String editor10, editor11, tech12, employee13, employee14, auditor15, other30;

    @BeforeAll
    void seed() {
        jdbc.update("INSERT INTO dir_users (user_id, company_id, employee_no, first_name, last_name, email, employment_status, roles) VALUES "
                + "(10,1,'K10','Ed','Itor','k10@x.test','ACTIVE','KNOWLEDGE_EDITOR'),(11,1,'K11','Eda','Itor','k11@x.test','ACTIVE','KNOWLEDGE_EDITOR'),"
                + "(12,1,'K12','Tom','Tech','k12@x.test','ACTIVE','TECHNICIAN'),(13,1,'K13','Eve','Employee','k13@x.test','ACTIVE','EMPLOYEE'),"
                + "(14,1,'K14','Eli','Employee','k14@x.test','ACTIVE','EMPLOYEE'),(15,1,'K15','Ann','Auditor','k15@x.test','ACTIVE','AUDITOR'),"
                + "(16,1,'K16','Ian','Gone','k16@x.test','INACTIVE','KNOWLEDGE_EDITOR'),(30,2,'K30','Oscar','Other','k30@x.test','ACTIVE','KNOWLEDGE_EDITOR')");
        editor10 = TestJwt.bearer(10, 1, "KNOWLEDGE_EDITOR");
        editor11 = TestJwt.bearer(11, 1, "KNOWLEDGE_EDITOR");
        tech12 = TestJwt.bearer(12, 1, "TECHNICIAN");
        employee13 = TestJwt.bearer(13, 1, "EMPLOYEE");
        employee14 = TestJwt.bearer(14, 1, "EMPLOYEE");
        auditor15 = TestJwt.bearer(15, 1, "AUDITOR");
        other30 = TestJwt.bearer(30, 2, "KNOWLEDGE_EDITOR");
    }

    JsonNode call(org.springframework.test.web.servlet.RequestBuilder rb, int status) throws Exception {
        String body = mvc.perform(rb).andExpect(status().is(status)).andReturn().getResponse().getContentAsString();
        return body.isBlank() ? null : json.readTree(body);
    }

    JsonNode post(String token, String path, String body, int status) throws Exception {
        return call(MockMvcRequestBuilders.post(path).header("Authorization", token).contentType(MediaType.APPLICATION_JSON).content(body), status);
    }

    JsonNode get(String token, String path, int status) throws Exception {
        return call(MockMvcRequestBuilders.get(path).header("Authorization", token), status);
    }

    JsonNode patch(String token, String path, String body, int status) throws Exception {
        return call(MockMvcRequestBuilders.patch(path).header("Authorization", token).contentType(MediaType.APPLICATION_JSON).content(body), status);
    }

    long create(String token, String title, String body) throws Exception {
        return post(token, "/api/v1/kb/articles", "{\"title\":\"" + title + "\",\"body\":\"" + body + "\"}", 201).get("articleId").asLong();
    }

    void status(String token, long id, String to, int expected) throws Exception {
        post(token, "/api/v1/kb/articles/" + id + "/status", "{\"status\":\"" + to + "\"}", expected);
    }

    /** Creates an article and publishes it with a second pair of eyes. */
    long published(String title, String body) throws Exception {
        long id = create(tech12, title, body);
        status(tech12, id, "UNDER_REVIEW", 200);
        status(editor10, id, "PUBLISHED", 200);
        return id;
    }

    Set<Long> recipients(long id, String type) {
        Set<Long> out = new HashSet<>();
        for (String p : jdbc.queryForList("SELECT payload FROM outbox_events WHERE topic='knowledge.events' AND event_type=? AND message_key=?",
                String.class, type, String.valueOf(id))) {
            json.readTree(p).get("payload").get("notification").get("notifyUserIds").forEach(n -> out.add(n.asLong()));
        }
        return out;
    }

    @Test
    void workflowWithFourEyes() throws Exception {
        long id = create(tech12, "Reset the VPN client", "Open the client and press reset to restore the tunnel.");
        get(employee13, "/api/v1/kb/articles/" + id, 404);
        get(tech12, "/api/v1/kb/articles/" + id, 200);
        status(employee13, id, "UNDER_REVIEW", 404);
        status(tech12, id, "PUBLISHED", 422);
        status(tech12, id, "UNDER_REVIEW", 200);
        // editors (active ones) are notified, not the author, not inactive editors
        assertThat(recipients(id, "article.review_requested")).containsExactlyInAnyOrder(10L, 11L);
        status(tech12, id, "PUBLISHED", 403);
        status(employee13, id, "PUBLISHED", 404);
        JsonNode pub = post(editor10, "/api/v1/kb/articles/" + id + "/status", "{\"status\":\"PUBLISHED\"}", 200);
        assertThat(pub.get("status").asString()).isEqualTo("PUBLISHED");
        assertThat(pub.get("publishedAt").isNull()).isFalse();
        assertThat(recipients(id, "article.published")).containsExactly(12L);
        status(tech12, id, "RETIRED", 403);
        status(editor11, id, "RETIRED", 200);
        status(editor11, id, "UNDER_REVIEW", 422);
        status(editor11, id, "DRAFT", 200);
        assertThat(jdbc.queryForList("SELECT event_type FROM outbox_events WHERE topic='audit.events' AND message_key=? ORDER BY id",
                String.class, String.valueOf(id))).containsExactly("audit.create", "audit.status_change", "audit.status_change",
                "audit.status_change", "audit.status_change");
    }

    @Test
    void editorWhoIsAuthorCannotPublishOwnArticle() throws Exception {
        long id = create(editor10, "Editor article", "An article written by an editor and nobody else.");
        status(editor10, id, "UNDER_REVIEW", 200);
        assertThat(recipients(id, "article.review_requested")).containsExactly(11L);
        status(editor10, id, "PUBLISHED", 403);
        status(editor11, id, "PUBLISHED", 200);
    }

    @Test
    void editRules() throws Exception {
        long id = create(tech12, "Draft to edit", "Initial body text for the draft article.");
        patch(employee13, "/api/v1/kb/articles/" + id, "{\"title\":\"Hack\"}", 404);
        assertThat(patch(tech12, "/api/v1/kb/articles/" + id, "{\"title\":\"Edited title\"}", 200).get("title").asString()).isEqualTo("Edited title");
        status(tech12, id, "UNDER_REVIEW", 200);
        patch(tech12, "/api/v1/kb/articles/" + id, "{\"title\":\"Too late\"}", 403);
        patch(editor11, "/api/v1/kb/articles/" + id, "{\"title\":\"Editor fixed\"}", 200);
        status(editor11, id, "PUBLISHED", 200);
        patch(editor11, "/api/v1/kb/articles/" + id, "{\"title\":\"Nope\"}", 422);
        patch(tech12, "/api/v1/kb/articles/" + id, "{\"title\":\"Nope\"}", 403);
    }

    @Test
    void createRolesAndValidation() throws Exception {
        post(employee13, "/api/v1/kb/articles", "{\"title\":\"Employee article\",\"body\":\"Employees cannot author articles.\"}", 403);
        post(auditor15, "/api/v1/kb/articles", "{\"title\":\"Auditor article\",\"body\":\"Auditors cannot author articles.\"}", 403);
        post(tech12, "/api/v1/kb/articles", "{\"title\":\"x\",\"body\":\"short\"}", 400);
        mvc.perform(MockMvcRequestBuilders.get("/api/v1/kb/articles")).andExpect(status().isUnauthorized());
    }

    @Test
    void searchIsRankedAndUsesWebsearchSyntax() throws Exception {
        long strong = published("Wireguard tunnel guide", "wireguard wireguard wireguard configuration for the wireguard tunnel");
        long weak = published("Remote access overview", "Among many tools there is wireguard and also openvpn mentioned briefly here");
        long other = published("Printer queue", "Clear the printer queue and restart the spooler service");
        long both = published("Wireguard printer sharing", "wireguard and printer together");

        JsonNode r = get(employee13, "/api/v1/kb/articles?q=wireguard", 200);
        List<Long> ids = r.get("items").valueStream().map(n -> n.get("articleId").asLong()).toList();
        assertThat(ids).containsExactlyInAnyOrder(strong, weak, both).doesNotContain(other);
        assertThat(ids.get(0)).isEqualTo(strong);
        assertThat(r.get("items").get(0).get("rank").asDouble()).isGreaterThan(r.get("items").get(2).get("rank").asDouble());
        assertThat(r.get("items").get(0).get("body").isNull()).isTrue();
        assertThat(r.get("items").get(0).get("snippet").asString()).contains("wireguard");

        List<Long> excl = get(employee13, "/api/v1/kb/articles?q=wireguard%20-printer", 200).get("items").valueStream()
                .map(n -> n.get("articleId").asLong()).toList();
        assertThat(excl).containsExactlyInAnyOrder(strong, weak);
        List<Long> phrase = get(employee13, "/api/v1/kb/articles?q=%22printer%20queue%22", 200).get("items").valueStream()
                .map(n -> n.get("articleId").asLong()).toList();
        assertThat(phrase).containsExactly(other);
        assertThat(get(employee13, "/api/v1/kb/articles?q=wireguard&size=1&page=2", 200).get("items")).hasSize(1);
        assertThat(get(employee13, "/api/v1/kb/articles?q=wireguard&size=1", 200).get("total").asInt()).isEqualTo(3);
    }

    @Test
    void employeesSeeOnlyPublishedPlusOwnDrafts() throws Exception {
        long draft = create(tech12, "Zebrafish draft", "A zebrafish draft that is not yet reviewed by anyone.");
        long review = create(tech12, "Zebrafish in review", "A zebrafish article that is waiting for review.");
        status(tech12, review, "UNDER_REVIEW", 200);
        long pub = published("Zebrafish published", "A zebrafish article that everybody can read now.");
        Set<Long> employee = ids(get(employee13, "/api/v1/kb/articles?q=zebrafish", 200));
        assertThat(employee).containsExactly(pub);
        assertThat(ids(get(tech12, "/api/v1/kb/articles?q=zebrafish", 200))).containsExactlyInAnyOrder(draft, review, pub);
        assertThat(ids(get(editor11, "/api/v1/kb/articles?q=zebrafish", 200))).containsExactlyInAnyOrder(draft, review, pub);
        assertThat(ids(get(auditor15, "/api/v1/kb/articles?q=zebrafish&status=DRAFT,UNDER_REVIEW", 200))).containsExactlyInAnyOrder(draft, review);
        // forcing a status filter does not widen what an employee may see
        assertThat(ids(get(employee13, "/api/v1/kb/articles?q=zebrafish&status=DRAFT", 200))).isEmpty();
        get(employee13, "/api/v1/kb/articles/" + draft, 404);
        get(employee13, "/api/v1/kb/articles/" + pub, 200);
    }

    Set<Long> ids(JsonNode page) {
        Set<Long> s = new HashSet<>();
        page.get("items").forEach(n -> s.add(n.get("articleId").asLong()));
        return s;
    }

    @Test
    void readingCountsViewsOnlyWhenPublished() throws Exception {
        long id = create(tech12, "View counting", "Body of the view counting article.");
        assertThat(get(tech12, "/api/v1/kb/articles/" + id, 200).get("viewCount").asInt()).isZero();
        status(tech12, id, "UNDER_REVIEW", 200);
        status(editor10, id, "PUBLISHED", 200);
        assertThat(get(employee13, "/api/v1/kb/articles/" + id, 200).get("viewCount").asInt()).isEqualTo(1);
        assertThat(get(employee14, "/api/v1/kb/articles/" + id, 200).get("viewCount").asInt()).isEqualTo(2);
    }

    @Test
    void feedbackIsIdempotentAndChangesMoveCounters() throws Exception {
        long id = published("Feedback article", "An article people can vote on after publication.");
        String url = "/api/v1/kb/articles/" + id + "/feedback";
        JsonNode a = post(employee13, url, "{\"helpful\":true}", 200);
        assertThat(a.get("helpfulCount").asInt()).isEqualTo(1);
        a = post(employee13, url, "{\"helpful\":true}", 200);
        assertThat(a.get("helpfulCount").asInt()).isEqualTo(1);
        a = post(employee14, url, "{\"helpful\":true,\"comment\":\"great\"}", 200);
        assertThat(a.get("helpfulCount").asInt()).isEqualTo(2);
        a = post(employee13, url, "{\"helpful\":false}", 200);
        assertThat(a.get("helpfulCount").asInt()).isEqualTo(1);
        assertThat(a.get("notHelpfulCount").asInt()).isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM article_feedback WHERE article_id=?", Long.class, id)).isEqualTo(2);
        post(employee13, url, "{}", 400);

        long draft = create(tech12, "Draft feedback", "Feedback is refused on drafts, always.");
        post(tech12, "/api/v1/kb/articles/" + draft + "/feedback", "{\"helpful\":true}", 422);
        post(employee13, "/api/v1/kb/articles/" + draft + "/feedback", "{\"helpful\":true}", 404);
    }

    @Test
    void tenantIsolation() throws Exception {
        long id = published("Tenant article", "Only company one may read this tenant article.");
        get(other30, "/api/v1/kb/articles/" + id, 404);
        post(other30, "/api/v1/kb/articles/" + id + "/feedback", "{\"helpful\":true}", 404);
        status(other30, id, "RETIRED", 404);
        assertThat(get(other30, "/api/v1/kb/articles?q=tenant", 200).get("total").asInt()).isZero();
        long theirs = post(other30, "/api/v1/kb/articles", "{\"title\":\"Other tenant\",\"body\":\"Written in the other company.\"}", 403).isNull() ? 0 : 0;
        assertThat(theirs).isZero();
    }

    @Test
    void domainEventsReachKafka() throws Exception {
        long id = published("Kafka article", "Published so that the events reach the topic.");
        long end = System.currentTimeMillis() + 20_000;
        boolean found = false;
        Properties p = new Properties();
        p.put("bootstrap.servers", kafkaAdmin.getConfigurationProperties().get("bootstrap.servers"));
        p.put("group.id", "it-" + System.nanoTime());
        p.put("auto.offset.reset", "earliest");
        try (var c = new KafkaConsumer<>(p, new StringDeserializer(), new StringDeserializer())) {
            c.subscribe(List.of("knowledge.events"));
            while (!found && System.currentTimeMillis() < end) {
                for (var r : c.poll(Duration.ofMillis(500))) {
                    if (r.key().equals(String.valueOf(id)) && r.value().contains("article.published")) found = true;
                }
            }
        }
        assertThat(found).isTrue();
    }
}
