package com.esmhub.directory.service.org;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TeamRepository extends JpaRepository<Team, Long> {
    List<Team> findByCompanyIdOrderByName(long companyId);
    @org.springframework.data.jpa.repository.Query(value = "SELECT team_id FROM team_members WHERE user_id = ?1", nativeQuery = true)
    List<Long> findTeamIdsOfUser(long userId);
}
