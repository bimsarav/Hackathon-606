package com.esmhub.directory;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;

/** Replica of a directory user (read-only for the hosting service). */
@Entity
@Table(name = "dir_users")
public class DirUser {
    @Id @Column(name = "user_id") private Long userId;
    @Column(name = "company_id") private long companyId;
    @Column(name = "employee_no") private String employeeNo;
    @Column(name = "first_name") private String firstName;
    @Column(name = "last_name") private String lastName;
    private String email;
    @Column(name = "office_id") private Long officeId;
    @Column(name = "department_id") private Long departmentId;
    @Column(name = "manager_id") private Long managerId;
    @Column(name = "employment_status") private String employmentStatus;
    private String roles;

    protected DirUser() {}

    public DirUser(Long userId) { this.userId = userId; }

    void apply(com.esmhub.common.contracts.DirectoryContracts.UserSnapshot s) {
        companyId = s.companyId(); employeeNo = s.employeeNo(); firstName = s.firstName(); lastName = s.lastName();
        email = s.email(); officeId = s.officeId(); departmentId = s.departmentId(); managerId = s.managerId();
        employmentStatus = s.employmentStatus(); roles = s.roles() == null ? "" : String.join(",", s.roles());
    }

    public Long getUserId() { return userId; }
    public long getCompanyId() { return companyId; }
    public String getEmployeeNo() { return employeeNo; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public String getFullName() { return firstName + " " + lastName; }
    public String getEmail() { return email; }
    public Long getOfficeId() { return officeId; }
    public Long getDepartmentId() { return departmentId; }
    public Long getManagerId() { return managerId; }
    public String getEmploymentStatus() { return employmentStatus; }
    public boolean isActive() { return !"INACTIVE".equals(employmentStatus); }
    public Set<String> getRoles() {
        return roles == null || roles.isBlank() ? Set.of() : Arrays.stream(roles.split(",")).collect(Collectors.toSet());
    }
}
