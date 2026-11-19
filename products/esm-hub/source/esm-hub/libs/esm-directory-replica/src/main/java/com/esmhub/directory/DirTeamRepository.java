package com.esmhub.directory;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DirTeamRepository extends JpaRepository<DirTeam, Long> {
    List<DirTeam> findByCompanyId(long companyId);
}
