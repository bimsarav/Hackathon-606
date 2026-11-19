package com.esmhub.directory.service.user;

import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RoleRepository extends JpaRepository<AppRole, Long> {
    List<AppRole> findByNameIn(Collection<String> names);
    List<AppRole> findAllByOrderByName();
}
