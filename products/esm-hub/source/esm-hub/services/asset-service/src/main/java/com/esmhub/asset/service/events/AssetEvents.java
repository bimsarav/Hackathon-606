package com.esmhub.asset.service.events;

import com.esmhub.asset.service.asset.Asset;
import com.esmhub.common.contracts.DomainContracts.AssetSnapshot;
import com.esmhub.common.contracts.DomainContracts.DomainEvent;
import com.esmhub.common.contracts.DomainContracts.NotificationIntent;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Publishes asset state snapshots and domain events (via the outbox, in the caller's transaction). */
@Component
public class AssetEvents {
    private final OutboxPublisher outbox;

    public AssetEvents(OutboxPublisher outbox) { this.outbox = outbox; }

    public void snapshot(Asset a) { snapshot(outbox, a); }

    void snapshot(OutboxPublisher pub, Asset a) {
        pub.publish(Topics.ASSET_ASSETS, "asset.snapshot", "asset", a.getId(), a.getCompanyId(),
                new AssetSnapshot(a.getId(), a.getCompanyId(), a.getAssetTag(), a.getAssetType(), a.getStatus(),
                        a.getAssignedUserId(), a.getOfficeId(), a.getPurchaseDate(), a.getWarrantyEnd(), a.getPurchaseCost()));
    }

    /** asset.assigned: in-app notification for the assignee only (no email). */
    public void assigned(Asset a, long assigneeId) {
        String desc = ((a.getManufacturer() == null ? "" : a.getManufacturer() + " ") + (a.getModel() == null ? "" : a.getModel())).trim();
        Map<String, Object> facts = new LinkedHashMap<>();
        facts.put("assetTag", a.getAssetTag());
        facts.put("assigneeId", assigneeId);
        outbox.publish(Topics.ASSET_EVENTS, "asset.assigned", "asset", a.getId(), a.getCompanyId(),
                new DomainEvent("ASSET", String.valueOf(a.getId()), a.getAssetTag(),
                        new NotificationIntent(List.of(assigneeId), "Asset " + a.getAssetTag() + " assigned to you",
                                desc.isEmpty() ? a.getAssetType() : desc, "/assets/" + a.getId(), false), facts));
    }
}
