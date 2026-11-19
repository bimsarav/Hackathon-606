package com.esmhub.directory.service.user;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.List;

/** API records of the user resource. */
public final class UserDtos {
    private UserDtos() {}

    public record UserView(long userId, String employeeNo, String firstName, String lastName, String email, Long officeId,
                           Long departmentId, Long managerId, String employmentStatus, List<String> roles, List<Long> teamIds) {}

    public record CreateUser(@NotBlank @Size(max = 20) String employeeNo, @NotBlank @Size(max = 60) String firstName,
                             @NotBlank @Size(max = 60) String lastName, @NotBlank @Email @Size(max = 160) String email,
                             Long officeId, Long departmentId, Long managerId,
                             @NotEmpty List<@NotBlank String> roles, @Size(max = 200) String initialPassword) {}

    public record UpdateUser(@Size(min = 1, max = 60) String firstName, @Size(min = 1, max = 60) String lastName,
                             Long officeId, Long departmentId, Long managerId,
                             @Pattern(regexp = "ACTIVE|INACTIVE|ON_LEAVE") String employmentStatus,
                             List<@NotBlank String> roles, List<Long> teamIds) {}

    public record SetPassword(@NotBlank @Size(max = 200) String newPassword) {}
}
