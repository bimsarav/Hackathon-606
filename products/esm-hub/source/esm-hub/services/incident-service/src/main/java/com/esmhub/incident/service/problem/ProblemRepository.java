package com.esmhub.incident.service.problem;

import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface ProblemRepository extends JpaRepository<Problem, Long> {
    @Query(value = "SELECT nextval(pg_get_serial_sequence('problems', 'problem_id'))", nativeQuery = true)
    long nextId();

    Optional<Problem> findByIdAndCompanyId(long id, long companyId);

    @Query("select p from Problem p where p.companyId = :company and (:status is null or p.status in :statuses) "
            + "and (:knownError is null or p.knownError = :knownError) "
            + "and (:q is null or lower(p.problemNo) like :q or lower(p.title) like :q)")
    Page<Problem> search(long company, String status, java.util.Collection<String> statuses, Boolean knownError,
                         String q, Pageable pageable);

    @Query("select p from Problem p join p.incidentIds i where i = ?1 order by p.id")
    List<Problem> findLinkedTo(long incidentId);
}
