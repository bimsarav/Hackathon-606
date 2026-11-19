package com.esmhub.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.knowledge.service.article.Article;
import com.esmhub.knowledge.service.article.ArticleRules;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.test.util.ReflectionTestUtils;

class ArticleRulesTest {
    @ParameterizedTest
    @CsvSource({"DRAFT,UNDER_REVIEW,true", "DRAFT,PUBLISHED,false", "UNDER_REVIEW,PUBLISHED,true", "UNDER_REVIEW,DRAFT,true",
            "UNDER_REVIEW,RETIRED,false", "PUBLISHED,RETIRED,true", "PUBLISHED,DRAFT,true", "PUBLISHED,UNDER_REVIEW,false",
            "RETIRED,DRAFT,true", "RETIRED,PUBLISHED,false"})
    void workflow(String from, String to, boolean allowed) {
        assertThat(ArticleRules.canMove(from, to)).isEqualTo(allowed);
    }

    Article article(int helpful, int notHelpful) {
        Article a = new Article(1, "T", "body body body", null, 5L);
        ReflectionTestUtils.setField(a, "helpfulCount", helpful);
        ReflectionTestUtils.setField(a, "notHelpfulCount", notHelpful);
        return a;
    }

    @Test
    void firstVoteIncrementsOneCounter() {
        Article a = article(3, 1);
        a.applyVote(null, true);
        assertThat(a.getHelpfulCount()).isEqualTo(4);
        assertThat(a.getNotHelpfulCount()).isEqualTo(1);
        a.applyVote(null, false);
        assertThat(a.getNotHelpfulCount()).isEqualTo(2);
    }

    @Test
    void repeatingTheSameVoteIsIdempotent() {
        Article a = article(3, 1);
        a.applyVote(true, true);
        a.applyVote(false, false);
        assertThat(a.getHelpfulCount()).isEqualTo(3);
        assertThat(a.getNotHelpfulCount()).isEqualTo(1);
    }

    @Test
    void changingAVoteMovesTheCounters() {
        Article a = article(3, 1);
        a.applyVote(true, false);
        assertThat(a.getHelpfulCount()).isEqualTo(2);
        assertThat(a.getNotHelpfulCount()).isEqualTo(2);
        a.applyVote(false, true);
        assertThat(a.getHelpfulCount()).isEqualTo(3);
        assertThat(a.getNotHelpfulCount()).isEqualTo(1);
    }

    @Test
    void publishingStampsReviewerAndDate() {
        Article a = article(0, 0);
        a.moveTo("PUBLISHED", 9L);
        assertThat(a.getReviewedBy()).isEqualTo(9L);
        assertThat(a.getPublishedAt()).isNotNull();
    }
}
