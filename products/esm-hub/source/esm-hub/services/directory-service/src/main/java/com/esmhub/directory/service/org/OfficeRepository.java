package com.esmhub.directory.service.org;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OfficeRepository extends JpaRepository<Office, Long> {
    List<Office> findByCompanyIdOrderByName(long companyId);

}
