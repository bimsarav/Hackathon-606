package com.esmhub.knowledge.service.article;

import java.util.Map;
import java.util.Set;

/** Pure rules of the KB publishing workflow (FR-10). */
public final class ArticleRules {
    private ArticleRules() {}

    public static final String DRAFT = "DRAFT", UNDER_REVIEW = "UNDER_REVIEW", PUBLISHED = "PUBLISHED", RETIRED = "RETIRED";

    public static final Map<String, Set<String>> FLOW = Map.of(
            DRAFT, Set.of(UNDER_REVIEW),
            UNDER_REVIEW, Set.of(PUBLISHED, DRAFT),
            PUBLISHED, Set.of(RETIRED, DRAFT),
            RETIRED, Set.of(DRAFT));

    public static boolean canMove(String from, String to) {
        return FLOW.getOrDefault(from, Set.of()).contains(to);
    }
}
