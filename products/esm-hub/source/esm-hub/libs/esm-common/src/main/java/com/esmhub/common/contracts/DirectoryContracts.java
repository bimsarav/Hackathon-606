package com.esmhub.common.contracts;

import java.util.List;

/** Payloads of the directory state topics (compacted). Owned by directory-service; consumed via esm-directory-replica. */
public final class DirectoryContracts {
    private DirectoryContracts() {}

    public record UserSnapshot(long userId, long companyId, String employeeNo, String firstName, String lastName,
                               String email, Long officeId, Long departmentId, Long managerId, String employmentStatus,
                               List<String> roles, List<Long> teamIds) {}

    public record TeamSnapshot(long teamId, long companyId, String name, int supportLevel, Long managerUserId,
                               boolean active, List<Long> memberIds) {}

    public record ServiceSnapshot(long serviceId, long companyId, String name, Long categoryId, String categoryName,
                                  Long owningTeamId, boolean active) {}

    public record OfficeSnapshot(long officeId, long companyId, String name, String city, String country, String timezone) {}
}
