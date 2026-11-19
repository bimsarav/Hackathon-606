package com.esmhub.directory.service.events;

import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.SnapshotSource;
import com.esmhub.directory.service.org.BusinessServiceRepository;
import com.esmhub.directory.service.org.OfficeRepository;
import com.esmhub.directory.service.org.TeamRepository;
import com.esmhub.directory.service.user.UserRepository;
import org.springframework.stereotype.Component;

/** Republishes all directory state on first start / after the demo seed, so every replica is complete. */
@Component
public class DirectorySnapshotSource implements SnapshotSource {
    private final DirectoryEvents events;
    private final UserRepository users;
    private final TeamRepository teams;
    private final BusinessServiceRepository services;
    private final OfficeRepository offices;

    public DirectorySnapshotSource(DirectoryEvents events, UserRepository users, TeamRepository teams,
                                   BusinessServiceRepository services, OfficeRepository offices) {
        this.events = events;
        this.users = users;
        this.teams = teams;
        this.services = services;
        this.offices = offices;
    }

    @Override public String name() { return "directory"; }
    @Override public int version() { return 1; }

    @Override
    public void publishAll(OutboxPublisher publisher) {
        offices.findAll().forEach(o -> events.office(publisher, o));
        teams.findAll().forEach(t -> events.team(publisher, t));
        services.findAll().forEach(s -> events.service(publisher, s));
        users.findAll().forEach(u -> events.user(publisher, u, teams.findTeamIdsOfUser(u.getId())));
    }
}
