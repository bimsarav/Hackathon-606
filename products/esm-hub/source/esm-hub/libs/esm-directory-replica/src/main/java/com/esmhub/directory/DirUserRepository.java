package com.esmhub.directory;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface DirUserRepository extends JpaRepository<DirUser, Long> {
    List<DirUser> findByCompanyId(long companyId);

    @Query("select u from DirUser u where u.companyId = ?1 and u.employmentStatus <> 'INACTIVE' "
            + "and concat(',', u.roles, ',') like concat('%,', ?2, ',%')")
    List<DirUser> findActiveByCompanyAndRole(long companyId, String role);
}
