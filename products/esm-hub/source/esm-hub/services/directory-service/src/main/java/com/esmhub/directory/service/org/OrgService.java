package com.esmhub.directory.service.org;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.service.events.DirectoryEvents;
import com.esmhub.directory.service.org.OrgDtos.*;
import com.esmhub.directory.service.user.AppRole;
import com.esmhub.directory.service.user.RoleRepository;
import com.esmhub.directory.service.user.UserRepository;
import java.time.DateTimeException;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Organisation hierarchy and service master data (FR-2, FR-15). Reads for all users; writes per role. */
@Service
public class OrgService {
    private final OfficeRepository offices;
    private final DepartmentRepository departments;
    private final TeamRepository teams;
    private final ServiceCategoryRepository categories;
    private final BusinessServiceRepository services;
    private final RoleRepository roles;
    private final UserRepository users;
    private final DirectoryEvents events;
    private final AuditPublisher audit;

    public OrgService(OfficeRepository offices, DepartmentRepository departments, TeamRepository teams,
                      ServiceCategoryRepository categories, BusinessServiceRepository services, RoleRepository roles,
                      UserRepository users, DirectoryEvents events, AuditPublisher audit) {
        this.offices = offices;
        this.departments = departments;
        this.teams = teams;
        this.categories = categories;
        this.services = services;
        this.roles = roles;
        this.users = users;
        this.events = events;
        this.audit = audit;
    }

    static OfficeView view(Office o) { return new OfficeView(o.getId(), o.getName(), o.getCity(), o.getCountry(), o.getTimezone()); }
    static TeamView view(Team t) {
        return new TeamView(t.getId(), t.getName(), t.getSupportLevel(), t.getManagerUserId(), t.isActive(),
                t.getMemberIds().stream().sorted().toList());
    }
    static ServiceView view(BusinessService s) {
        return new ServiceView(s.getId(), s.getName(), s.getDescription(), s.getCategoryId(), s.getOwningTeamId(), s.isActive());
    }

    @Transactional(readOnly = true)
    public Reference reference(CurrentUser me) {
        long c = me.companyId();
        return new Reference(
                offices.findByCompanyIdOrderByName(c).stream().map(OrgService::view).toList(),
                departments.findByCompanyIdOrderByName(c).stream().map(d -> new DepartmentView(d.getId(), d.getName(), d.getCostCentre())).toList(),
                teams.findByCompanyIdOrderByName(c).stream().map(OrgService::view).toList(),
                categories.findAll().stream().map(x -> new CategoryView(x.getId(), x.getName(), x.getParentId())).toList(),
                services.findByCompanyIdOrderByName(c).stream().map(OrgService::view).toList(),
                roles.findAllByOrderByName().stream().map(AppRole::getName).toList());
    }

    @Transactional(readOnly = true)
    public List<MemberView> members(CurrentUser me, long teamId) {
        Team t = team(me, teamId);
        return users.findAllById(t.getMemberIds()).stream()
                .map(u -> new MemberView(u.getId(), u.fullName(), u.getEmail(), u.roleNames().stream().sorted().toList()))
                .sorted((a, b) -> a.name().compareToIgnoreCase(b.name())).toList();
    }

    Team team(CurrentUser me, Long id) {
        return teams.findById(id).filter(t -> t.getCompanyId() == me.companyId()).orElseThrow(() -> NotFoundException.of("Team", id));
    }

    @Transactional
    public OfficeView saveOffice(CurrentUser me, Long id, OfficeInput in) {
        me.require(Role.ADMIN);
        try {
            ZoneId.of(in.timezone());
        } catch (DateTimeException e) {
            throw new BusinessRuleException("Unknown IANA timezone: " + in.timezone());
        }
        Office o = id == null ? new Office(me.companyId())
                : offices.findById(id).filter(x -> x.getCompanyId() == me.companyId()).orElseThrow(() -> NotFoundException.of("Office", id));
        o.update(in.name(), in.city(), in.country(), in.timezone());
        offices.save(o);
        audit.record("OFFICE", o.getId(), id == null ? "CREATE" : "UPDATE", null, Map.of("name", in.name(), "timezone", in.timezone()));
        events.office(o);
        return view(o);
    }

    @Transactional
    public DepartmentView createDepartment(CurrentUser me, DepartmentInput in) {
        me.require(Role.ADMIN);
        Department d = departments.save(new Department(me.companyId(), in.name(), in.costCentre()));
        audit.record("DEPARTMENT", d.getId(), "CREATE", null, Map.of("name", in.name()));
        return new DepartmentView(d.getId(), d.getName(), d.getCostCentre());
    }

    @Transactional
    public TeamView saveTeam(CurrentUser me, Long id, TeamInput in) {
        me.require(Role.ADMIN);
        if (in.managerUserId() != null && users.findById(in.managerUserId()).filter(u -> u.getCompanyId() == me.companyId()).isEmpty()) {
            throw NotFoundException.of("User", in.managerUserId());
        }
        Team t = id == null ? new Team(me.companyId()) : team(me, id);
        t.update(in.name(), in.supportLevel(), in.managerUserId(), in.active());
        teams.save(t);
        audit.record("TEAM", t.getId(), id == null ? "CREATE" : "UPDATE", null, Map.of("name", in.name(), "active", in.active()));
        events.team(t);
        return view(t);
    }

    @Transactional
    public CategoryView createCategory(CurrentUser me, CategoryInput in) {
        me.require(Role.SERVICE_MANAGER, Role.ADMIN);
        if (in.parentId() != null && categories.findById(in.parentId()).isEmpty()) {
            throw NotFoundException.of("Category", in.parentId());
        }
        ServiceCategory c = categories.save(new ServiceCategory(in.name(), in.parentId()));
        audit.record("CATEGORY", c.getId(), "CREATE", null, Map.of("name", in.name()));
        return new CategoryView(c.getId(), c.getName(), c.getParentId());
    }

    @Transactional
    public ServiceView saveService(CurrentUser me, Long id, ServiceInput in) {
        me.require(Role.SERVICE_MANAGER, Role.ADMIN);
        if (in.owningTeamId() != null) {
            team(me, in.owningTeamId());
        }
        if (in.categoryId() != null && categories.findById(in.categoryId()).isEmpty()) {
            throw NotFoundException.of("Category", in.categoryId());
        }
        BusinessService s = id == null ? new BusinessService(me.companyId())
                : services.findById(id).filter(x -> x.getCompanyId() == me.companyId()).orElseThrow(() -> NotFoundException.of("Service", id));
        s.update(in.name(), in.description(), in.categoryId(), in.owningTeamId(), in.active());
        services.save(s);
        audit.record("SERVICE", s.getId(), id == null ? "CREATE" : "UPDATE", null, Map.of("name", in.name(), "active", in.active()));
        events.service(s);
        return view(s);
    }
}
