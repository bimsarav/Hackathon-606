package com.esmhub.knowledge.service.article;

import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

public interface ArticleRepository extends JpaRepository<Article, Long> {
    Optional<Article> findByIdAndCompanyId(Long id, long companyId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from Article a where a.id = ?1 and a.companyId = ?2")
    Optional<Article> lockByIdAndCompanyId(Long id, long companyId);

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update Article a set a.viewCount = a.viewCount + 1 where a.id = ?1")
    int incrementViews(Long id);
}
