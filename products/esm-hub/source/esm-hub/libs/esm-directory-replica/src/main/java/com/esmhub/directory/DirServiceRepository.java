package com.esmhub.directory;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DirServiceRepository extends JpaRepository<DirService, Long> {
    List<DirService> findByCompanyId(long companyId);
}
