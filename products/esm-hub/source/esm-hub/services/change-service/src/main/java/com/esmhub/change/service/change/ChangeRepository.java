package com.esmhub.change.service.change;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ChangeRepository extends JpaRepository<Change, Long>, JpaSpecificationExecutor<Change> {
    @Query("select c from Change c where c.companyId = :company and c.status in :statuses and c.plannedStart is not null "
            + "and c.plannedEnd is not null and c.plannedStart < :to and c.plannedEnd > :from order by c.plannedStart, c.id")
    List<Change> window(@Param("company") long company, @Param("statuses") Collection<String> statuses,
                        @Param("from") Instant from, @Param("to") Instant to);
}
