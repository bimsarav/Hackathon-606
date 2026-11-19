package com.esmhub.common.events;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.transaction.support.TransactionTemplate;

/** Runs pending {@link SnapshotSource}s once the application is ready. */
public class SnapshotBootstrapper {
    private static final Logger log = LoggerFactory.getLogger(SnapshotBootstrapper.class);
    private final List<SnapshotSource> sources;
    private final SnapshotStateRepository states;
    private final OutboxPublisher publisher;
    private final TransactionTemplate tx;

    public SnapshotBootstrapper(List<SnapshotSource> sources, SnapshotStateRepository states, OutboxPublisher publisher,
                                TransactionTemplate tx) {
        this.sources = sources;
        this.states = states;
        this.publisher = publisher;
        this.tx = tx;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void bootstrap() {
        for (SnapshotSource s : sources) {
            tx.executeWithoutResult(st -> {
                int current = states.findById(s.name()).map(SnapshotState::getVersion).orElse(0);
                if (current < s.version()) {
                    s.publishAll(publisher);
                    states.save(new SnapshotState(s.name(), s.version()));
                    log.info("snapshot_published source={} version={}", s.name(), s.version());
                }
            });
        }
    }
}
