package com.esmhub.directory.service.org;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;

public final class OrgDtos {
    private OrgDtos() {}

    public record OfficeView(long officeId, String name, String city, String country, String timezone) {}
    public record DepartmentView(long departmentId, String name, String costCentre) {}
    public record TeamView(long teamId, String name, int supportLevel, Long managerUserId, boolean active, List<Long> memberIds) {}
    public record CategoryView(long categoryId, String name, Long parentId) {}
    public record ServiceView(long serviceId, String name, String description, Long categoryId, Long owningTeamId, boolean active) {}
    public record Reference(List<OfficeView> offices, List<DepartmentView> departments, List<TeamView> teams,
                            List<CategoryView> categories, List<ServiceView> services, List<String> roles) {}
    public record MemberView(long userId, String name, String email, List<String> roles) {}

    public record OfficeInput(@NotBlank @Size(max = 100) String name, @NotBlank @Size(max = 80) String city,
                              @NotBlank @Size(max = 80) String country, @NotBlank @Size(max = 60) String timezone) {}
    public record DepartmentInput(@NotBlank @Size(max = 100) String name, @Size(max = 30) String costCentre) {}
    public record TeamInput(@NotBlank @Size(max = 100) String name, @Min(1) @Max(3) int supportLevel, Long managerUserId,
                            boolean active) {}
    public record CategoryInput(@NotBlank @Size(max = 80) String name, Long parentId) {}
    public record ServiceInput(@NotBlank @Size(max = 120) String name, @Size(max = 5000) String description,
                               Long categoryId, Long owningTeamId, boolean active) {}
}
