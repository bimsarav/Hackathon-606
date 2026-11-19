package com.esmhub.incident.service.incident;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;

public interface IncidentRepository extends JpaRepository<Incident, Long>, JpaSpecificationExecutor<Incident> {
    @Query(value = "SELECT nextval(pg_get_serial_sequence('incidents', 'incident_id'))", nativeQuery = true)
    long nextId();

    Optional<Incident> findByIdAndCompanyId(long id, long companyId);

    /** Open incidents with an SLA, locked for the scan (other replicas skip them). */
    @Query(value = "SELECT i.* FROM incidents i JOIN ticket_statuses s ON s.status_id = i.status_id "
            + "WHERE NOT s.is_closed AND i.due_at IS NOT NULL ORDER BY i.incident_id FOR UPDATE OF i SKIP LOCKED",
            nativeQuery = true)
    List<Incident> lockOpenWithSla();

    @Query(value = "SELECT * FROM incidents WHERE status_id = ?1 AND resolved_at < ?2 ORDER BY incident_id "
            + "FOR UPDATE SKIP LOCKED", nativeQuery = true)
    List<Incident> lockResolvedBefore(int resolvedStatusId, Instant cutoff);
}
