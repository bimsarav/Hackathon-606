package com.esmhub.incident.service.reference;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AssignmentRuleRepository extends JpaRepository<AssignmentRule, Long> {
    List<AssignmentRule> findByCompanyIdOrderBySortOrderAscIdAsc(long companyId);
}
