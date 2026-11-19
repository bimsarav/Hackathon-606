package com.esmhub.common.events;

import org.springframework.data.jpa.repository.JpaRepository;

public interface SnapshotStateRepository extends JpaRepository<SnapshotState, String> {
}
