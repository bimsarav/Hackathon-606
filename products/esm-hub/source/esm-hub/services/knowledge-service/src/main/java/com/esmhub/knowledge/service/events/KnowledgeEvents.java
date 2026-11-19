package com.esmhub.knowledge.service.events;

import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import com.esmhub.knowledge.service.article.Article;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Domain events for notification-service (in-app only). */
@Component
public class KnowledgeEvents {
    private final OutboxPublisher outbox;

    public KnowledgeEvents(OutboxPublisher outbox) { this.outbox = outbox; }

    public void reviewRequested(Article a, List<Long> editorIds) {
        if (editorIds.isEmpty()) return;
        publish("article.review_requested", a, new NotificationIntent(editorIds, "Article for review: " + a.getTitle(),
                "An article is waiting for your review.", "/kb/" + a.getId(), false));
    }

    public void published(Article a, long authorId) {
        publish("article.published", a, new NotificationIntent(List.of(authorId), "Article published: " + a.getTitle(),
                "Your article is now published.", "/kb/" + a.getId(), false));
    }

    private void publish(String type, Article a, NotificationIntent n) {
        outbox.publish(Topics.KNOWLEDGE_EVENTS, type, "article", a.getId(), a.getCompanyId(),
                new DomainEvent("KNOWLEDGE_ARTICLE", String.valueOf(a.getId()), "KB-" + a.getId(), n,
                        Map.of("title", a.getTitle(), "status", a.getStatus())));
    }
}
