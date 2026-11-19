package com.esmhub.knowledge.service.article;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "articles")
public class Article {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "article_id") private Long id;
    @Column(name = "company_id") private long companyId;
    private String title;
    private String body;
    @Column(name = "category_id") private Long categoryId;
    @Column(name = "author_id") private Long authorId;
    @Column(name = "reviewed_by") private Long reviewedBy;
    private String status = ArticleRules.DRAFT;
    @Column(name = "view_count") private int viewCount;
    @Column(name = "helpful_count") private int helpfulCount;
    @Column(name = "not_helpful_count") private int notHelpfulCount;
    @Column(name = "published_at") private Instant publishedAt;
    @Column(name = "created_at") private Instant createdAt = Instant.now();
    @Column(name = "updated_at") private Instant updatedAt = Instant.now();

    protected Article() {}

    public Article(long companyId, String title, String body, Long categoryId, Long authorId) {
        this.companyId = companyId; this.title = title; this.body = body; this.categoryId = categoryId; this.authorId = authorId;
    }

    public void edit(String title, String body, Long categoryId) {
        if (title != null) this.title = title;
        if (body != null) this.body = body;
        if (categoryId != null) this.categoryId = categoryId;
        this.updatedAt = Instant.now();
    }

    public void moveTo(String to, long actorId) {
        this.status = to;
        if (ArticleRules.PUBLISHED.equals(to)) { this.publishedAt = Instant.now(); this.reviewedBy = actorId; }
        this.updatedAt = Instant.now();
    }

    /**
     * Moves the counters by the change in one user's vote. {@code previous} is null for a first vote. Repeating the same
     * vote changes nothing, so the endpoint is idempotent, and legacy seed counts stay intact.
     */
    public void applyVote(Boolean previous, boolean helpful) {
        if (previous != null && previous == helpful) return;
        if (Boolean.TRUE.equals(previous)) helpfulCount = Math.max(0, helpfulCount - 1);
        else if (Boolean.FALSE.equals(previous)) notHelpfulCount = Math.max(0, notHelpfulCount - 1);
        if (helpful) helpfulCount++; else notHelpfulCount++;
    }

    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public String getTitle() { return title; }
    public String getBody() { return body; }
    public Long getCategoryId() { return categoryId; }
    public Long getAuthorId() { return authorId; }
    public Long getReviewedBy() { return reviewedBy; }
    public String getStatus() { return status; }
    public int getViewCount() { return viewCount; }
    public int getHelpfulCount() { return helpfulCount; }
    public int getNotHelpfulCount() { return notHelpfulCount; }
    public Instant getPublishedAt() { return publishedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
