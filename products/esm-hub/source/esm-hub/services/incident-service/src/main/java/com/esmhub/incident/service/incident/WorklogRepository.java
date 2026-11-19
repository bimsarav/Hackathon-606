package com.esmhub.incident.service.incident;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface WorklogRepository extends JpaRepository<Worklog, Long> {
    List<Worklog> findByIncidentIdOrderByLoggedAtAscIdAsc(long incidentId);

    @Query("select coalesce(sum(w.minutesSpent), 0) from Worklog w where w.incidentId = ?1")
    long totalMinutes(long incidentId);
}
