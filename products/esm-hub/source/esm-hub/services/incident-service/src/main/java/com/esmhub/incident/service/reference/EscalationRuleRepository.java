package com.esmhub.incident.service.reference;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface EscalationRuleRepository extends JpaRepository<EscalationRule, Long> {
    @Query("select r from EscalationRule r where (r.companyId is null or r.companyId = ?1) order by r.id")
    List<EscalationRule> visible(long companyId);

    @Query("select r from EscalationRule r where r.active = true and r.trigger = ?3 "
            + "and (r.companyId is null or r.companyId = ?1) and (r.priorityId is null or r.priorityId = ?2) order by r.id")
    List<EscalationRule> matching(long companyId, int priorityId, String trigger);
}
