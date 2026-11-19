package com.esmhub.directory.service.events;

import com.esmhub.common.contracts.DirectoryContracts.OfficeSnapshot;
import com.esmhub.common.contracts.DirectoryContracts.ServiceSnapshot;
import com.esmhub.common.contracts.DirectoryContracts.TeamSnapshot;
import com.esmhub.common.contracts.DirectoryContracts.UserSnapshot;
import com.esmhub.common.events.OutboxPublisher;
import com.esmhub.common.events.Topics;
import com.esmhub.directory.service.org.BusinessService;
import com.esmhub.directory.service.org.Office;
import com.esmhub.directory.service.org.ServiceCategoryRepository;
import com.esmhub.directory.service.org.Team;
import com.esmhub.directory.service.org.TeamRepository;
import com.esmhub.directory.service.user.User;
import java.util.List;
import org.springframework.stereotype.Component;

/** Publishes the current state of directory aggregates to the compacted directory.* topics (via the outbox). */
@Component
public class DirectoryEvents {
    private final OutboxPublisher outbox;
    private final TeamRepository teams;
    private final ServiceCategoryRepository categories;

    public DirectoryEvents(OutboxPublisher outbox, TeamRepository teams, ServiceCategoryRepository categories) {
        this.outbox = outbox;
        this.teams = teams;
        this.categories = categories;
    }

    public void user(User u) {
        user(outbox, u, teams.findTeamIdsOfUser(u.getId()));
    }

    void user(OutboxPublisher pub, User u, List<Long> teamIds) {
        pub.publish(Topics.DIRECTORY_USERS, "user.snapshot", "user", u.getId(), u.getCompanyId(),
                new UserSnapshot(u.getId(), u.getCompanyId(), u.getEmployeeNo(), u.getFirstName(), u.getLastName(),
                        u.getEmail(), u.getOfficeId(), u.getDepartmentId(), u.getManagerId(), u.getEmploymentStatus(),
                        u.roleNames().stream().sorted().toList(), teamIds.stream().sorted().toList()));
    }

    public void team(Team t) { team(outbox, t); }

    void team(OutboxPublisher pub, Team t) {
        pub.publish(Topics.DIRECTORY_TEAMS, "team.snapshot", "team", t.getId(), t.getCompanyId(),
                new TeamSnapshot(t.getId(), t.getCompanyId(), t.getName(), t.getSupportLevel(), t.getManagerUserId(),
                        t.isActive(), t.getMemberIds().stream().sorted().toList()));
    }

    public void service(BusinessService s) { service(outbox, s); }

    void service(OutboxPublisher pub, BusinessService s) {
        String cat = s.getCategoryId() == null ? null : categories.findById(s.getCategoryId()).map(c -> c.getName()).orElse(null);
        pub.publish(Topics.DIRECTORY_SERVICES, "service.snapshot", "service", s.getId(), s.getCompanyId(),
                new ServiceSnapshot(s.getId(), s.getCompanyId(), s.getName(), s.getCategoryId(), cat, s.getOwningTeamId(), s.isActive()));
    }

    public void office(Office o) { office(outbox, o); }

    void office(OutboxPublisher pub, Office o) {
        pub.publish(Topics.DIRECTORY_OFFICES, "office.snapshot", "office", o.getId(), o.getCompanyId(),
                new OfficeSnapshot(o.getId(), o.getCompanyId(), o.getName(), o.getCity(), o.getCountry(), o.getTimezone()));
    }
}
