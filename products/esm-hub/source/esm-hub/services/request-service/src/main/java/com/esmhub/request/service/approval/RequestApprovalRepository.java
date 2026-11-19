package com.esmhub.request.service.approval;

import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RequestApprovalRepository extends JpaRepository<RequestApproval, Long> {
    List<RequestApproval> findByRequestIdOrderByStepOrderAscIdAsc(long requestId);

    List<RequestApproval> findByRequestIdAndDecision(long requestId, String decision);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from RequestApproval a where a.id = :id")
    Optional<RequestApproval> lockById(@Param("id") long id);

    @Query("select a from RequestApproval a, ServiceRequest r where a.requestId = r.id and r.companyId = :company "
            + "and a.decision = 'PENDING' and (a.approverId = :me or (a.approverId is null and a.approverRole in :roles)) "
            + "order by a.createdAt, a.id")
    List<RequestApproval> pendingFor(@Param("company") long company, @Param("me") long me, @Param("roles") Collection<String> roles);

    @Query("select count(a) > 0 from RequestApproval a where a.requestId = :requestId "
            + "and (a.approverId = :me or (a.approverId is null and a.approverRole in :roles))")
    boolean involves(@Param("requestId") long requestId, @Param("me") long me, @Param("roles") Collection<String> roles);
}
