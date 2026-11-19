package com.esmhub.knowledge.service.article;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.knowledge.service.article.ArticleDtos.*;
import com.esmhub.knowledge.service.events.KnowledgeEvents;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Knowledge base: search, workflow with four-eyes publishing, feedback (FR-10). */
@Service
public class ArticleService {
    static final Role[] AUTHORS = {Role.KNOWLEDGE_EDITOR, Role.SERVICE_DESK_AGENT, Role.TECHNICIAN, Role.TEAM_LEAD, Role.SERVICE_MANAGER};
    static final Role[] SEE_ALL = {Role.KNOWLEDGE_EDITOR, Role.AUDITOR, Role.ADMIN};
    static final int SNIPPET = 240;

    private final ArticleRepository articles;
    private final ArticleFeedbackRepository feedback;
    private final ArticleSearch search;
    private final DirectoryLookup directory;
    private final KnowledgeEvents events;
    private final AuditPublisher audit;

    public ArticleService(ArticleRepository articles, ArticleFeedbackRepository feedback, ArticleSearch search,
                          DirectoryLookup directory, KnowledgeEvents events, AuditPublisher audit) {
        this.articles = articles;
        this.feedback = feedback;
        this.search = search;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
    }

    private ArticleView view(Article a, boolean full, Double rank) {
        String body = a.getBody();
        return new ArticleView(a.getId(), a.getTitle(), full ? body : null,
                full ? null : body.substring(0, Math.min(SNIPPET, body.length())), a.getCategoryId(), a.getAuthorId(),
                a.getAuthorId() == null ? null : directory.name(a.getAuthorId()), a.getStatus(), a.getViewCount(),
                a.getHelpfulCount(), a.getNotHelpfulCount(), a.getPublishedAt(), a.getUpdatedAt(), rank);
    }

    private static Map<String, Object> auditFields(Article a) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("title", a.getTitle());
        m.put("status", a.getStatus());
        m.put("category_id", a.getCategoryId());
        m.put("published_at", a.getPublishedAt() == null ? null : a.getPublishedAt().toString());
        m.put("reviewed_by", a.getReviewedBy());
        return m;
    }

    private static boolean isAuthor(CurrentUser me, Article a) { return a.getAuthorId() != null && a.getAuthorId() == me.userId(); }

    private static boolean visible(CurrentUser me, Article a) {
        return ArticleRules.PUBLISHED.equals(a.getStatus()) || me.has(SEE_ALL) || isAuthor(me, a);
    }

    private Article scoped(CurrentUser me, long id) {
        return articles.findByIdAndCompanyId(id, me.companyId()).filter(a -> visible(me, a))
                .orElseThrow(() -> NotFoundException.of("Article", id));
    }

    @Transactional(readOnly = true)
    public PageResponse<ArticleView> search(CurrentUser me, String q, Long categoryId, String status, int page, int size) {
        PageResponse.pageable(page, size, Sort.unsorted()); // validates paging
        List<String> statuses = status == null || status.isBlank() ? List.of()
                : List.of(status.toUpperCase().split(","));
        var res = search.search(me.companyId(), me.userId(), me.has(SEE_ALL), q, categoryId, statuses, (page - 1) * size, size);
        Map<Long, Article> byId = articles.findAllById(res.hits().stream().map(ArticleSearch.Hit::articleId).toList()).stream()
                .collect(Collectors.toMap(Article::getId, x -> x));
        List<ArticleView> items = new ArrayList<>();
        res.hits().forEach(h -> items.add(view(byId.get(h.articleId()), false, h.rank())));
        return new PageResponse<>(items, res.total(), page, size);
    }

    /** Reading a published article counts a view. */
    @Transactional
    public ArticleView read(CurrentUser me, long id) {
        Article a = scoped(me, id);
        if (ArticleRules.PUBLISHED.equals(a.getStatus())) {
            articles.incrementViews(a.getId());
            a = articles.findById(id).orElseThrow();
        }
        return view(a, true, null);
    }

    @Transactional
    public ArticleView create(CurrentUser me, CreateArticle in) {
        me.require(AUTHORS);
        Article a = new Article(me.companyId(), in.title().trim(), in.body(), in.categoryId(), me.userId());
        articles.saveAndFlush(a);
        audit.record("KNOWLEDGE_ARTICLE", a.getId(), "CREATE", null, auditFields(a));
        return view(a, true, null);
    }

    @Transactional
    public ArticleView edit(CurrentUser me, long id, UpdateArticle in) {
        Article a = scoped(me, id);
        boolean editor = me.has(Role.KNOWLEDGE_EDITOR);
        if (!(editor || (isAuthor(me, a) && ArticleRules.DRAFT.equals(a.getStatus())))) {
            throw new ForbiddenException("Only the author (while in draft) or a knowledge editor can edit.");
        }
        if (ArticleRules.PUBLISHED.equals(a.getStatus())) {
            throw new BusinessRuleException("Move a published article back to DRAFT before editing.");
        }
        Map<String, Object> before = auditFields(a);
        a.edit(in.title() == null ? null : in.title().trim(), in.body(), in.categoryId());
        articles.saveAndFlush(a);
        audit.record("KNOWLEDGE_ARTICLE", a.getId(), "UPDATE", before, auditFields(a));
        return view(a, true, null);
    }

    /** Workflow: the author submits for review; only a knowledge editor who is not the author can publish (four-eyes). */
    @Transactional
    public ArticleView changeStatus(CurrentUser me, long id, String to) {
        Article a = scoped(me, id);
        String from = a.getStatus();
        if (!ArticleRules.canMove(from, to)) {
            throw new BusinessRuleException("Transition " + from + " -> " + to + " is not allowed.");
        }
        boolean author = isAuthor(me, a), editor = me.has(Role.KNOWLEDGE_EDITOR);
        switch (to) {
            case ArticleRules.UNDER_REVIEW -> {
                if (!(author || editor)) throw new ForbiddenException("Only the author or an editor can submit for review.");
            }
            case ArticleRules.PUBLISHED -> {
                if (author) throw new ForbiddenException("Authors cannot publish their own article (four-eyes review).");
                me.require(Role.KNOWLEDGE_EDITOR);
            }
            case ArticleRules.RETIRED -> me.require(Role.KNOWLEDGE_EDITOR);
            default -> { // DRAFT
                if (ArticleRules.UNDER_REVIEW.equals(from)) {
                    if (!(author || editor)) throw new ForbiddenException("Not allowed.");
                } else {
                    me.require(Role.KNOWLEDGE_EDITOR);
                }
            }
        }
        Map<String, Object> before = auditFields(a);
        a.moveTo(to, me.userId());
        articles.saveAndFlush(a);
        if (ArticleRules.UNDER_REVIEW.equals(to)) {
            List<Long> editors = directory.activeUserIdsWithRole(me.companyId(), Role.KNOWLEDGE_EDITOR.name()).stream()
                    .filter(u -> u != me.userId() && !u.equals(a.getAuthorId())).sorted().toList();
            events.reviewRequested(a, editors);
        } else if (ArticleRules.PUBLISHED.equals(to) && a.getAuthorId() != null) {
            events.published(a, a.getAuthorId());
        }
        audit.record("KNOWLEDGE_ARTICLE", a.getId(), "STATUS_CHANGE", before, auditFields(a));
        return view(a, true, null);
    }

    /** One vote per user and article; voting again replaces the earlier vote and moves the counters. */
    @Transactional
    public ArticleView vote(CurrentUser me, long id, boolean helpful, String comment) {
        scoped(me, id);
        Article a = articles.lockByIdAndCompanyId(id, me.companyId()).orElseThrow(() -> NotFoundException.of("Article", id));
        if (!ArticleRules.PUBLISHED.equals(a.getStatus())) {
            throw new BusinessRuleException("Feedback is only accepted on published articles.");
        }
        var key = new ArticleFeedback.Key(a.getId(), me.userId());
        var existing = feedback.findById(key);
        Boolean previous = existing.map(ArticleFeedback::isHelpful).orElse(null);
        if (existing.isPresent()) {
            existing.get().vote(helpful, comment);
            feedback.save(existing.get());
        } else {
            feedback.save(new ArticleFeedback(a.getId(), me.userId(), helpful, comment));
        }
        a.applyVote(previous, helpful);
        articles.saveAndFlush(a);
        return view(a, true, null);
    }
}
