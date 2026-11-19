package com.esmhub.common.security;

import java.util.EnumSet;
import java.util.Set;

/** Platform roles (JWT claim {@code roles}). Every authenticated user also has employee capabilities. */
public enum Role {
    EMPLOYEE, SERVICE_DESK_AGENT, TECHNICIAN, TEAM_LEAD, SERVICE_MANAGER, CHANGE_MANAGER, ASSET_MANAGER,
    KNOWLEDGE_EDITOR, ADMIN, AUDITOR;

    /** Resolver-side roles that work tickets. */
    public static final Set<Role> STAFF = EnumSet.of(SERVICE_DESK_AGENT, TECHNICIAN, TEAM_LEAD, SERVICE_MANAGER);
}
