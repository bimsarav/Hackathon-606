package com.esmhub.common.events;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.kafka.config.TopicBuilder;

/** Topic names and builders. Owners declare their topics as NewTopic beans. */
public final class Topics {
    private Topics() {}

    public static final String DIRECTORY_USERS = "directory.users";
    public static final String DIRECTORY_TEAMS = "directory.teams";
    public static final String DIRECTORY_SERVICES = "directory.services";
    public static final String DIRECTORY_OFFICES = "directory.offices";
    public static final String INCIDENT_INCIDENTS = "incident.incidents";
    public static final String INCIDENT_PROBLEMS = "incident.problems";
    public static final String INCIDENT_EVENTS = "incident.events";
    public static final String REQUEST_REQUESTS = "request.requests";
    public static final String REQUEST_EVENTS = "request.events";
    public static final String CHANGE_CHANGES = "change.changes";
    public static final String CHANGE_EVENTS = "change.events";
    public static final String ASSET_ASSETS = "asset.assets";
    public static final String ASSET_EVENTS = "asset.events";
    public static final String KNOWLEDGE_EVENTS = "knowledge.events";
    public static final String AUDIT_EVENTS = "audit.events";

    /** Latest-state topic (log compaction, keeps tombstones 1 day). */
    public static NewTopic compacted(String name) {
        return TopicBuilder.name(name).partitions(3).replicas(1).compact()
                .config("delete.retention.ms", "86400000").config("min.compaction.lag.ms", "0").build();
    }

    /** Domain event topic with time-based retention. */
    public static NewTopic events(String name, int retentionDays) {
        return TopicBuilder.name(name).partitions(3).replicas(1)
                .config("retention.ms", String.valueOf(retentionDays * 86_400_000L)).build();
    }
}
