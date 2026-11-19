package com.esmhub.knowledge.service.article;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ArticleFeedbackRepository extends JpaRepository<ArticleFeedback, ArticleFeedback.Key> {
}
