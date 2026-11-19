package com.esmhub.directory;

import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/** Read API over the replica for business code (assignee validation, approvers, recipients, names). */
public class DirectoryLookup {
    private final DirUserRepository users;
    private final DirTeamRepository teams;
    private final DirServiceRepository services;
    private final DirOfficeRepository offices;

    public DirectoryLookup(DirUserRepository users, DirTeamRepository teams,
                           DirServiceRepository services, DirOfficeRepository offices) {
        this.users = users;
        this.teams = teams;
        this.services = services;
        this.offices = offices;
    }

    public Optional<DirUser> user(Long id) { return id == null ? Optional.empty() : users.findById(id); }
    public Optional<DirTeam> team(Long id) { return id == null ? Optional.empty() : teams.findById(id); }
    public Optional<DirService> service(Long id) { return id == null ? Optional.empty() : services.findById(id); }
    public Optional<DirOffice> office(Long id) { return id == null ? Optional.empty() : offices.findById(id); }

    /** User in the given company, or empty (tenant check included). */
    public Optional<DirUser> userInCompany(Long id, long companyId) {
        return user(id).filter(u -> u.getCompanyId() == companyId);
    }

    public Optional<DirTeam> teamInCompany(Long id, long companyId) {
        return team(id).filter(t -> t.getCompanyId() == companyId);
    }

    public Optional<DirService> serviceInCompany(Long id, long companyId) {
        return service(id).filter(s -> s.getCompanyId() == companyId);
    }

    public boolean isMember(Long teamId, Long userId) {
        return team(teamId).map(t -> t.getMemberIds().contains(userId)).orElse(false);
    }

    public String name(Long userId) {
        return user(userId).map(DirUser::getFullName).orElse(userId == null ? null : "User #" + userId);
    }

    public Set<Long> activeUserIdsWithRole(long companyId, String role) {
        return users.findActiveByCompanyAndRole(companyId, role).stream().map(DirUser::getUserId).collect(Collectors.toSet());
    }

    public Set<Long> teamLead(Long teamId) {
        return team(teamId).map(DirTeam::getManagerUserId).map(Set::of).orElse(Set.of());
    }

    /** IANA timezone of the user's office, or null if unknown. */
    public String timezoneOf(Long userId) {
        return user(userId).map(DirUser::getOfficeId).flatMap(this::office).map(DirOffice::getTimezone).orElse(null);
    }
}
