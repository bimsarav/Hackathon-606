package com.esmhub.directory;

import com.esmhub.common.contracts.DirectoryContracts.OfficeSnapshot;
import com.esmhub.common.contracts.DirectoryContracts.ServiceSnapshot;
import com.esmhub.common.contracts.DirectoryContracts.TeamSnapshot;
import com.esmhub.common.contracts.DirectoryContracts.UserSnapshot;
import com.esmhub.common.events.EventEnvelope;
import com.esmhub.common.events.Topics;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

/**
 * Applies directory state topics to the replica tables. State messages are idempotent upserts (last value per key
 * wins, ordered within a partition), so no processed-event bookkeeping is needed. Null values are tombstones.
 * Each service uses its own consumer group and starts from the earliest offset, so a fresh replica is rebuilt.
 */
public class DirectoryReplicaListener {
    private final JsonMapper mapper;
    private final DirUserRepository users;
    private final DirTeamRepository teams;
    private final DirServiceRepository services;
    private final DirOfficeRepository offices;

    public DirectoryReplicaListener(JsonMapper mapper, DirUserRepository users, DirTeamRepository teams,
                                    DirServiceRepository services, DirOfficeRepository offices) {
        this.mapper = mapper;
        this.users = users;
        this.teams = teams;
        this.services = services;
        this.offices = offices;
    }

    private <T> T payload(String json, Class<T> type) {
        EventEnvelope env = mapper.readValue(json, EventEnvelope.class);
        return mapper.treeToValue(env.payload(), type);
    }

    @Transactional
    @KafkaListener(topics = Topics.DIRECTORY_USERS, groupId = "${spring.application.name}.directory",
            properties = "auto.offset.reset=earliest")
    public void onUser(ConsumerRecord<String, String> rec) {
        long id = Long.parseLong(rec.key());
        if (rec.value() == null) { users.deleteById(id); return; }
        UserSnapshot s = payload(rec.value(), UserSnapshot.class);
        DirUser u = users.findById(id).orElseGet(() -> new DirUser(id));
        u.apply(s);
        users.save(u);
    }

    @Transactional
    @KafkaListener(topics = Topics.DIRECTORY_TEAMS, groupId = "${spring.application.name}.directory",
            properties = "auto.offset.reset=earliest")
    public void onTeam(ConsumerRecord<String, String> rec) {
        long id = Long.parseLong(rec.key());
        if (rec.value() == null) { teams.deleteById(id); return; }
        TeamSnapshot s = payload(rec.value(), TeamSnapshot.class);
        DirTeam t = teams.findById(id).orElseGet(() -> new DirTeam(id));
        t.apply(s);
        teams.save(t);
    }

    @Transactional
    @KafkaListener(topics = Topics.DIRECTORY_SERVICES, groupId = "${spring.application.name}.directory",
            properties = "auto.offset.reset=earliest")
    public void onService(ConsumerRecord<String, String> rec) {
        long id = Long.parseLong(rec.key());
        if (rec.value() == null) { services.deleteById(id); return; }
        ServiceSnapshot s = payload(rec.value(), ServiceSnapshot.class);
        DirService d = services.findById(id).orElseGet(() -> new DirService(id));
        d.apply(s);
        services.save(d);
    }

    @Transactional
    @KafkaListener(topics = Topics.DIRECTORY_OFFICES, groupId = "${spring.application.name}.directory",
            properties = "auto.offset.reset=earliest")
    public void onOffice(ConsumerRecord<String, String> rec) {
        long id = Long.parseLong(rec.key());
        if (rec.value() == null) { offices.deleteById(id); return; }
        OfficeSnapshot s = payload(rec.value(), OfficeSnapshot.class);
        DirOffice o = offices.findById(id).orElseGet(() -> new DirOffice(id));
        o.apply(s);
        offices.save(o);
    }
}
