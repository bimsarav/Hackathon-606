package com.esmhub.common.security;

import com.esmhub.common.web.ForbiddenException;
import java.util.Arrays;
import java.util.Set;

/** The authenticated caller, built from the JWT. Never take the actor's identity from a request body. */
public record CurrentUser(long userId, long companyId, Set<String> roles, Set<Long> teamIds, String name, String email) {

    public boolean has(Role... any) {
        return Arrays.stream(any).anyMatch(r -> roles.contains(r.name()));
    }

    public boolean isStaff() {
        return Role.STAFF.stream().anyMatch(r -> roles.contains(r.name()));
    }

    public boolean inTeam(Long teamId) {
        return teamId != null && teamIds.contains(teamId);
    }

    /** Throws 403 unless the caller holds at least one of the roles. */
    public void require(Role... any) {
        if (!has(any)) {
            throw new ForbiddenException("Your role does not allow this action.");
        }
    }
}
