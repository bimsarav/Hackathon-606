package com.esmhub.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.knowledge.service.article.*;
import com.esmhub.knowledge.service.article.ArticleDtos.UpdateArticle;
import com.esmhub.knowledge.service.events.KnowledgeEvents;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class ArticleServiceTest {
    ArticleRepository articles = mock(ArticleRepository.class);
    ArticleFeedbackRepository feedback = mock(ArticleFeedbackRepository.class);
    ArticleSearch search = mock(ArticleSearch.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    KnowledgeEvents events = mock(KnowledgeEvents.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    ArticleService service = new ArticleService(articles, feedback, search, directory, events, audit);
    CurrentUser author = new CurrentUser(5, 1, Set.of("TECHNICIAN", "KNOWLEDGE_EDITOR"), Set.of(), "A", "a@x");
    CurrentUser plainAuthor = new CurrentUser(5, 1, Set.of("TECHNICIAN"), Set.of(), "A", "a@x");
    CurrentUser editor = new CurrentUser(6, 1, Set.of("KNOWLEDGE_EDITOR"), Set.of(), "E", "e@x");
    CurrentUser employee = new CurrentUser(7, 1, Set.of("EMPLOYEE"), Set.of(), "Y", "y@x");
    Article article;

    @BeforeEach
    void setUp() {
        article = new Article(1, "Reset VPN", "Steps to reset the VPN client", null, 5L);
        ReflectionTestUtils.setField(article, "id", 3L);
        when(articles.findByIdAndCompanyId(3L, 1L)).thenReturn(Optional.of(article));
        when(articles.lockByIdAndCompanyId(3L, 1L)).thenReturn(Optional.of(article));
        when(articles.saveAndFlush(any())).thenAnswer(i -> i.getArgument(0));
        when(directory.activeUserIdsWithRole(1L, "KNOWLEDGE_EDITOR")).thenReturn(Set.of(5L, 6L, 8L));
    }

    @Test
    void authorCannotPublishOwnArticleEvenAsEditor() {
        article.moveTo("UNDER_REVIEW", 5);
        assertThatThrownBy(() -> service.changeStatus(author, 3, "PUBLISHED")).isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("four-eyes");
        assertThat(article.getStatus()).isEqualTo("UNDER_REVIEW");
        verifyNoInteractions(events);
    }

    @Test
    void anotherEditorPublishesAndAuthorIsNotified() {
        article.moveTo("UNDER_REVIEW", 5);
        var v = service.changeStatus(editor, 3, "PUBLISHED");
        assertThat(v.status()).isEqualTo("PUBLISHED");
        verify(events).published(article, 5L);
        assertThat(article.getReviewedBy()).isEqualTo(6L);
    }

    @Test
    void submittingForReviewNotifiesEditorsButNotTheAuthor() {
        service.changeStatus(author, 3, "UNDER_REVIEW");
        verify(events).reviewRequested(article, List.of(6L, 8L));
    }

    @Test
    void nonEditorCannotPublishOrRetire() {
        article.moveTo("UNDER_REVIEW", 5);
        CurrentUser tech = new CurrentUser(9, 1, Set.of("TECHNICIAN"), Set.of(), "T", "t@x");
        article.moveTo("UNDER_REVIEW", 5);
        // a technician who is not the author cannot even see the unpublished article
        assertThatThrownBy(() -> service.changeStatus(tech, 3, "PUBLISHED")).isInstanceOf(NotFoundException.class);
        assertThatThrownBy(() -> service.changeStatus(plainAuthor, 3, "PUBLISHED")).isInstanceOf(ForbiddenException.class);
    }

    @Test
    void invalidTransitionIs422() {
        assertThatThrownBy(() -> service.changeStatus(editor, 3, "PUBLISHED")).isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> service.changeStatus(author, 3, "PUBLISHED")).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void authorEditsOwnDraftButNotAfterReview() {
        service.edit(plainAuthor, 3, new UpdateArticle("New title", null, null));
        assertThat(article.getTitle()).isEqualTo("New title");
        article.moveTo("UNDER_REVIEW", 5);
        assertThatThrownBy(() -> service.edit(plainAuthor, 3, new UpdateArticle("Again", null, null))).isInstanceOf(ForbiddenException.class);
    }

    @Test
    void publishedArticleCannotBeEditedEvenByEditor() {
        article.moveTo("PUBLISHED", 6);
        assertThatThrownBy(() -> service.edit(editor, 3, new UpdateArticle("Again", null, null))).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void employeesDoNotSeeUnpublishedArticles() {
        assertThatThrownBy(() -> service.read(employee, 3)).isInstanceOf(NotFoundException.class);
    }

    @Test
    void voteOnlyOnPublishedAndSecondVoteMovesCounters() {
        assertThatThrownBy(() -> service.vote(editor, 3, true, null)).isInstanceOf(BusinessRuleException.class);
        article.moveTo("PUBLISHED", 6);
        when(feedback.findById(any())).thenReturn(Optional.empty());
        assertThat(service.vote(employee, 3, true, null).helpfulCount()).isEqualTo(1);
        var existing = new ArticleFeedback(3, 7, true, null);
        when(feedback.findById(any())).thenReturn(Optional.of(existing));
        var v = service.vote(employee, 3, false, "meh");
        assertThat(v.helpfulCount()).isZero();
        assertThat(v.notHelpfulCount()).isEqualTo(1);
        assertThat(existing.isHelpful()).isFalse();
    }
}
