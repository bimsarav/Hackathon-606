package com.esmhub.common.events;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface OutboxRepository extends JpaRepository<OutboxEvent, Long> {
    /** Oldest unpublished rows, locked so that several instances never send the same row concurrently. */
    @Query(value = "SELECT * FROM outbox_events WHERE published_at IS NULL ORDER BY id LIMIT 200 FOR UPDATE SKIP LOCKED",
            nativeQuery = true)
    List<OutboxEvent> lockBatch();

    long countByPublishedAtIsNull();
}
