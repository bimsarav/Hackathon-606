package com.esmhub.directory.service.user;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

@Entity
@Table(name = "users")
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "user_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "employee_no") private String employeeNo;
    @Column(name = "first_name") private String firstName;
    @Column(name = "last_name") private String lastName;
    private String email;
    @Column(name = "office_id") private Long officeId;
    @Column(name = "department_id") private Long departmentId;
    @Column(name = "manager_id") private Long managerId;
    @Column(name = "employment_status") private String employmentStatus = "ACTIVE";
    @Column(name = "password_hash") private String passwordHash;
    @Column(name = "failed_logins") private int failedLogins;
    @Column(name = "locked_until") private Instant lockedUntil;
    @Column(name = "last_login_at") private Instant lastLoginAt;
    @Column(name = "created_at") private Instant createdAt = Instant.now();
    @ManyToMany(fetch = FetchType.EAGER)
    @JoinTable(name = "user_roles", joinColumns = @JoinColumn(name = "user_id"), inverseJoinColumns = @JoinColumn(name = "role_id"))
    private Set<AppRole> roles = new HashSet<>();

    protected User() {}

    public User(long companyId, String employeeNo, String email) {
        this.companyId = companyId; this.employeeNo = employeeNo; this.email = email;
    }

    public void updateProfile(String firstName, String lastName, Long officeId, Long departmentId, Long managerId) {
        this.firstName = firstName; this.lastName = lastName; this.officeId = officeId;
        this.departmentId = departmentId; this.managerId = managerId;
    }

    public Set<String> roleNames() { return roles.stream().map(AppRole::getName).collect(Collectors.toSet()); }
    public String fullName() { return firstName + " " + lastName; }
    public boolean isLocked(Instant now) { return lockedUntil != null && lockedUntil.isAfter(now); }

    /** Records a failed login; locks the account once the threshold is reached (BR: lockout 5 × / 15 min). */
    public void loginFailed(int maxFailures, Instant lockUntil) {
        failedLogins++;
        if (failedLogins >= maxFailures) { lockedUntil = lockUntil; failedLogins = 0; }
    }

    public void loginSucceeded(Instant now) { failedLogins = 0; lockedUntil = null; lastLoginAt = now; }

    public void setPassword(String hash) { this.passwordHash = hash; this.failedLogins = 0; this.lockedUntil = null; }
    public void setRoles(Set<AppRole> roles) { this.roles.clear(); this.roles.addAll(roles); }
    public void setEmploymentStatus(String s) { this.employmentStatus = s; }

    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public String getEmployeeNo() { return employeeNo; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public String getEmail() { return email; }
    public Long getOfficeId() { return officeId; }
    public Long getDepartmentId() { return departmentId; }
    public Long getManagerId() { return managerId; }
    public String getEmploymentStatus() { return employmentStatus; }
    public String getPasswordHash() { return passwordHash; }
    public int getFailedLogins() { return failedLogins; }
    public Instant getLockedUntil() { return lockedUntil; }
}
