package com.esmhub.incident.service.reference;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TicketStatusRepository extends JpaRepository<TicketStatus, Integer> {
    Optional<TicketStatus> findByName(String name);
}
