package com.esmhub.change.service.events;

import com.esmhub.change.service.change.ChangeRepository;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.SnapshotSource;
import org.springframework.stereotype.Component;

/** Republishes all changes to change.changes on first start / after the demo seed. */
@Component
public class ChangeSnapshotSource implements SnapshotSource {
    private final ChangeRepository changes;
    private final ChangeEvents events;

    public ChangeSnapshotSource(ChangeRepository changes, ChangeEvents events) {
        this.changes = changes;
        this.events = events;
    }

    @Override public String name() { return "change"; }
    @Override public int version() { return 1; }

    @Override
    public void publishAll(OutboxPublisher publisher) {
        changes.findAll().forEach(c -> events.snapshot(publisher, c));
    }
}
