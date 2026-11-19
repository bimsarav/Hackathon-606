package com.esmhub.common.events;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** Last published version of a state-topic snapshot per source. */
@Entity
@Table(name = "snapshot_state")
public class SnapshotState {
    @Id
    private String name;
    private int version;
    @Column(name = "published_at")
    private Instant publishedAt;

    protected SnapshotState() {}

    public SnapshotState(String name, int version) {
        this.name = name;
        this.version = version;
        this.publishedAt = Instant.now();
    }

    public int getVersion() { return version; }
}
