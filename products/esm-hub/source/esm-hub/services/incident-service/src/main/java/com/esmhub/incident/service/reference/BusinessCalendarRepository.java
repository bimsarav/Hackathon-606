package com.esmhub.incident.service.reference;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BusinessCalendarRepository extends JpaRepository<BusinessCalendar, Long> {
    List<BusinessCalendar> findAllByOrderByName();
    Optional<BusinessCalendar> findFirstByOrderById();
}
