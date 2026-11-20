package com.esmhub.change.service.approval;

import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ChangeApprovalRepository extends JpaRepository<ChangeApproval, Long> {
    List<ChangeApproval> findByChangeIdOrderByStepOrderAscIdAsc(long changeId);

    List<ChangeApproval> findByChangeIdAndDecision(long changeId, String decision);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from ChangeApproval a where a.id = :id")
    Optional<ChangeApproval> lockById(@Param("id") long id);

    @Query("select a from ChangeApproval a, Change c where a.changeId = c.id and c.companyId = :company "
            + "and a.decision = 'PENDING' and (a.approverId = :me or (a.approverId is null and a.approverRole in :roles)) "
            + "order by a.createdAt, a.id")
    List<ChangeApproval> pendingFor(@Param("company") long company, @Param("me") long me, @Param("roles") Collection<String> roles);

    @Query("select count(a) > 0 from ChangeApproval a where a.changeId = :changeId "
            + "and (a.approverId = :me or (a.approverId is null and a.approverRole in :roles))")
    boolean involves(@Param("changeId") long changeId, @Param("me") long me, @Param("roles") Collection<String> roles);
}
