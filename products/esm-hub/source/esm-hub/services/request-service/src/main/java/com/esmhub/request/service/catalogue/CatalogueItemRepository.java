package com.esmhub.request.service.catalogue;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CatalogueItemRepository extends JpaRepository<CatalogueItem, Long> {
    List<CatalogueItem> findByCompanyIdOrderByName(long companyId);
    List<CatalogueItem> findByCompanyIdAndActiveTrueOrderByName(long companyId);
}
