package com.esmhub.knowledge.service.article;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;

/** API records of the knowledge-base resource. {@code body} is null in search results (a snippet is given instead). */
public final class ArticleDtos {
    private ArticleDtos() {}

    public record ArticleView(long articleId, String title, String body, String snippet, Long categoryId, Long authorId,
                              String authorName, String status, int viewCount, int helpfulCount, int notHelpfulCount,
                              Instant publishedAt, Instant updatedAt, Double rank) {}

    public record CreateArticle(@NotBlank @Size(min = 3, max = 200) String title, @NotBlank @Size(min = 10, max = 100000) String body,
                                Long categoryId) {}

    public record UpdateArticle(@Size(min = 3, max = 200) String title, @Size(min = 10, max = 100000) String body, Long categoryId) {}

    public record ChangeStatus(@NotNull @Pattern(regexp = "DRAFT|UNDER_REVIEW|PUBLISHED|RETIRED") String status) {}

    public record Feedback(@NotNull Boolean helpful, @Size(max = 500) String comment) {}
}
