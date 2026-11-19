package com.esmhub.common.events;

/**
 * Implemented by owners of state topics. When {@link #version()} is higher than the stored version (first start,
 * after the demo seed, or after a deliberate bump), {@link #publishAll(OutboxPublisher)} republishes every aggregate.
 */
public interface SnapshotSource {
    String name();
    int version();
    void publishAll(OutboxPublisher publisher);
}
