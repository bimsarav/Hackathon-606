package com.esmhub.incident.service.reference;

import java.time.LocalDate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface SlaPolicyRepository extends JpaRepository<SlaPolicy, Long> {
    /** Candidates for an incident: most specific (service) first, then newest version. */
    @Query("select p from SlaPolicy p where p.priorityId = ?2 and (p.companyId is null or p.companyId = ?1) "
            + "and (p.serviceId is null or p.serviceId = ?3) and p.effectiveFrom <= ?4 "
            + "and (p.effectiveTo is null or p.effectiveTo >= ?4) "
            + "order by case when p.serviceId is null then 1 else 0 end, p.version desc, p.id desc")
    List<SlaPolicy> candidates(long companyId, int priorityId, Long serviceId, LocalDate onDate);

    @Query("select p from SlaPolicy p where (p.companyId is null or p.companyId = ?1) "
            + "order by p.priorityId, p.serviceId nulls first, p.version")
    List<SlaPolicy> visible(long companyId);

    @Query("select p from SlaPolicy p where p.priorityId = ?2 and (p.companyId is null or p.companyId = ?1) "
            + "and p.serviceId is null and p.effectiveTo is null")
    List<SlaPolicy> currentGeneral(long companyId, int priorityId);

    @Query("select p from SlaPolicy p where p.priorityId = ?2 and (p.companyId is null or p.companyId = ?1) "
            + "and p.serviceId = ?3 and p.effectiveTo is null")
    List<SlaPolicy> currentForService(long companyId, int priorityId, long serviceId);
}
