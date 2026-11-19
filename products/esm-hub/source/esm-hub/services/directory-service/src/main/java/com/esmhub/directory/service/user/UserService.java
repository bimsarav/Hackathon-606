package com.esmhub.directory.service.user;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.service.auth.PasswordPolicy;
import com.esmhub.directory.service.events.DirectoryEvents;
import com.esmhub.directory.service.org.DepartmentRepository;
import com.esmhub.directory.service.org.OfficeRepository;
import com.esmhub.directory.service.org.Team;
import com.esmhub.directory.service.org.TeamRepository;
import com.esmhub.directory.service.user.UserDtos.CreateUser;
import com.esmhub.directory.service.user.UserDtos.UpdateUser;
import com.esmhub.directory.service.user.UserDtos.UserView;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.Sort;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Users and roles (FR-1, FR-2). Directory reads for staff roles; writes for ADMIN only. */
@Service
public class UserService {
    static final Role[] DIRECTORY_READERS = {Role.SERVICE_DESK_AGENT, Role.TECHNICIAN, Role.TEAM_LEAD, Role.SERVICE_MANAGER,
            Role.CHANGE_MANAGER, Role.ASSET_MANAGER, Role.ADMIN, Role.AUDITOR};

    private final UserRepository users;
    private final RoleRepository roles;
    private final TeamRepository teams;
    private final OfficeRepository offices;
    private final DepartmentRepository departments;
    private final PasswordEncoder encoder;
    private final DirectoryEvents events;
    private final AuditPublisher audit;

    public UserService(UserRepository users, RoleRepository roles, TeamRepository teams, OfficeRepository offices,
                       DepartmentRepository departments, PasswordEncoder encoder, DirectoryEvents events, AuditPublisher audit) {
        this.users = users;
        this.roles = roles;
        this.teams = teams;
        this.offices = offices;
        this.departments = departments;
        this.encoder = encoder;
        this.events = events;
        this.audit = audit;
    }

    UserView view(User u) {
        return new UserView(u.getId(), u.getEmployeeNo(), u.getFirstName(), u.getLastName(), u.getEmail(), u.getOfficeId(),
                u.getDepartmentId(), u.getManagerId(), u.getEmploymentStatus(), u.roleNames().stream().sorted().toList(),
                teams.findTeamIdsOfUser(u.getId()).stream().sorted().toList());
    }

    @Transactional(readOnly = true)
    public PageResponse<UserView> search(CurrentUser me, String q, boolean includeInactive, int page, int size) {
        me.require(DIRECTORY_READERS);
        var p = users.search(me.companyId(), q == null || q.isBlank() ? null : q.trim(), includeInactive,
                PageResponse.pageable(page, size, Sort.by("lastName", "firstName")));
        return PageResponse.of(p, this::view);
    }

    @Transactional(readOnly = true)
    public UserView get(CurrentUser me, long id) {
        if (me.userId() != id) {
            me.require(DIRECTORY_READERS);
        }
        return view(scoped(me, id));
    }

    User scoped(CurrentUser me, Long id) {
        return users.findById(id).filter(u -> u.getCompanyId() == me.companyId())
                .orElseThrow(() -> NotFoundException.of("User", id));
    }

    @Transactional
    public UserView create(CurrentUser me, CreateUser req) {
        me.require(Role.ADMIN);
        if (users.findByEmailIgnoreCase(req.email()).isPresent() || users.existsByEmployeeNo(req.employeeNo())) {
            throw new ConflictException("A user with this email or employee number already exists.");
        }
        checkRefs(me, req.officeId(), req.departmentId(), req.managerId(), null);
        User u = new User(me.companyId(), req.employeeNo(), req.email().trim());
        u.updateProfile(req.firstName(), req.lastName(), req.officeId(), req.departmentId(), req.managerId());
        u.setRoles(resolveRoles(req.roles()));
        if (req.initialPassword() != null && !req.initialPassword().isBlank()) {
            PasswordPolicy.check(req.initialPassword());
            u.setPassword(encoder.encode(req.initialPassword()));
        }
        users.save(u);
        audit.record("USER", u.getId(), "CREATE", null, snapshot(u));
        events.user(u);
        return view(u);
    }

    @Transactional
    public UserView update(CurrentUser me, long id, UpdateUser req) {
        me.require(Role.ADMIN);
        User u = scoped(me, id);
        Map<String, Object> before = snapshot(u);
        checkRefs(me, req.officeId(), req.departmentId(), req.managerId(), id);
        u.updateProfile(req.firstName() != null ? req.firstName() : u.getFirstName(),
                req.lastName() != null ? req.lastName() : u.getLastName(),
                req.officeId() != null ? req.officeId() : u.getOfficeId(),
                req.departmentId() != null ? req.departmentId() : u.getDepartmentId(),
                req.managerId() != null ? req.managerId() : u.getManagerId());
        if (req.employmentStatus() != null) {
            u.setEmploymentStatus(req.employmentStatus());
        }
        String action = "UPDATE";
        if (req.roles() != null) {
            if (id == me.userId() && !req.roles().contains(Role.ADMIN.name())) {
                throw new BusinessRuleException("You cannot remove your own ADMIN role.");
            }
            u.setRoles(resolveRoles(req.roles()));
            action = "ROLE_CHANGE";
        }
        if (req.teamIds() != null) {
            setTeams(me, u, new HashSet<>(req.teamIds()));
        }
        audit.record("USER", u.getId(), action, before, snapshot(u));
        events.user(u);
        return view(u);
    }

    @Transactional
    public void resetPassword(CurrentUser me, long id, String password) {
        me.require(Role.ADMIN);
        User u = scoped(me, id);
        PasswordPolicy.check(password);
        u.setPassword(encoder.encode(password));
        audit.record("USER", id, "PASSWORD_RESET", null, null);
    }

    private void setTeams(CurrentUser me, User u, Set<Long> wanted) {
        for (Team t : teams.findByCompanyIdOrderByName(me.companyId())) {
            boolean member = t.getMemberIds().contains(u.getId());
            if (wanted.contains(t.getId()) != member) {
                if (member) t.getMemberIds().remove(u.getId()); else t.getMemberIds().add(u.getId());
                events.team(t);
            }
            wanted.remove(t.getId());
        }
        if (!wanted.isEmpty()) {
            throw NotFoundException.of("Team", wanted.iterator().next());
        }
        teams.flush();
    }

    private Set<AppRole> resolveRoles(List<String> names) {
        Set<String> wanted = new HashSet<>(names);
        var found = roles.findByNameIn(wanted);
        if (found.size() != wanted.size()) {
            throw new BusinessRuleException("Unknown role in list.");
        }
        return new HashSet<>(found);
    }

    private void checkRefs(CurrentUser me, Long officeId, Long departmentId, Long managerId, Long selfId) {
        if (officeId != null && offices.findById(officeId).filter(o -> o.getCompanyId() == me.companyId()).isEmpty()) {
            throw NotFoundException.of("Office", officeId);
        }
        if (departmentId != null && departments.findById(departmentId).filter(d -> d.getCompanyId() == me.companyId()).isEmpty()) {
            throw NotFoundException.of("Department", departmentId);
        }
        if (managerId != null) {
            if (managerId.equals(selfId)) {
                throw new BusinessRuleException("A user cannot be their own manager.");
            }
            scoped(me, managerId);
        }
    }

    private static Map<String, Object> snapshot(User u) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("email", u.getEmail());
        m.put("officeId", u.getOfficeId());
        m.put("departmentId", u.getDepartmentId());
        m.put("managerId", u.getManagerId());
        m.put("employmentStatus", u.getEmploymentStatus());
        m.put("roles", u.roleNames().stream().sorted().toList());
        return m;
    }
}
