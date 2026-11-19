package com.esmhub.asset.service.events;

import com.esmhub.asset.service.asset.AssetRepository;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.SnapshotSource;
import org.springframework.stereotype.Component;

/** Republishes all assets on first start / after the demo seed. */
@Component
public class AssetSnapshotSource implements SnapshotSource {
    private final AssetEvents events;
    private final AssetRepository assets;

    public AssetSnapshotSource(AssetEvents events, AssetRepository assets) {
        this.events = events;
        this.assets = assets;
    }

    @Override public String name() { return "asset"; }
    @Override public int version() { return 1; }

    @Override
    public void publishAll(OutboxPublisher publisher) {
        assets.findAll().forEach(a -> events.snapshot(publisher, a));
    }
}
