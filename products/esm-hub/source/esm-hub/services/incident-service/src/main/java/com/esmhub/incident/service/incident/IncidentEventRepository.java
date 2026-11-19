package com.esmhub.incident.service.incident;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentEventRepository extends JpaRepository<IncidentEvent, Long> {
    List<IncidentEvent> findByIncidentIdOrderByOccurredAtAscIdAsc(long incidentId);
}
