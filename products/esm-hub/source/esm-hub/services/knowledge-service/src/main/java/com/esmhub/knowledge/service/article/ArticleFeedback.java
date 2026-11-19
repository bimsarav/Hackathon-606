package com.esmhub.knowledge.service.article;

import jakarta.persistence.*;
import java.io.Serializable;
import java.time.Instant;

@Entity
@Table(name = "article_feedback")
@IdClass(ArticleFeedback.Key.class)
public class ArticleFeedback {
    @Id @Column(name = "article_id") private long articleId;
    @Id @Column(name = "user_id") private long userId;
    private boolean helpful;
    private String comment;
    @Column(name = "created_at") private Instant createdAt = Instant.now();

    protected ArticleFeedback() {}

    public ArticleFeedback(long articleId, long userId, boolean helpful, String comment) {
        this.articleId = articleId; this.userId = userId; this.helpful = helpful; this.comment = comment;
    }

    public void vote(boolean helpful, String comment) {
        this.helpful = helpful; this.comment = comment; this.createdAt = Instant.now();
    }

    public boolean isHelpful() { return helpful; }

    public record Key(long articleId, long userId) implements Serializable {
        public Key() { this(0, 0); }
    }
}
