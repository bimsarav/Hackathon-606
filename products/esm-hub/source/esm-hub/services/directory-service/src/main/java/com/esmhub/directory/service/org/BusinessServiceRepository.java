package com.esmhub.directory.service.org;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BusinessServiceRepository extends JpaRepository<BusinessService, Long> {
    List<BusinessService> findByCompanyIdOrderByName(long companyId);

}
