package com.esmhub.directory.service.user;

import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface UserRepository extends JpaRepository<User, Long> {
    @Query("select u from User u where lower(u.email) = lower(?1)")
    Optional<User> findByEmailIgnoreCase(String email);

    boolean existsByEmployeeNo(String employeeNo);

    @Query("""
            select u from User u where u.companyId = :company
              and (:q is null or lower(concat(u.firstName, ' ', u.lastName)) like lower(concat('%', cast(:q as string), '%'))
                   or lower(u.email) like lower(concat('%', cast(:q as string), '%')) or u.employeeNo like concat('%', cast(:q as string), '%'))
              and (:includeInactive = true or u.employmentStatus <> 'INACTIVE')
            """)
    Page<User> search(long company, String q, boolean includeInactive, Pageable pageable);
}
