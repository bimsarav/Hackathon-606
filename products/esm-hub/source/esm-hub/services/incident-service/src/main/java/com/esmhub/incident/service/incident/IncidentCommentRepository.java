package com.esmhub.incident.service.incident;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentCommentRepository extends JpaRepository<IncidentComment, Long> {
    List<IncidentComment> findByIncidentIdOrderByCreatedAtAscIdAsc(long incidentId);
}
