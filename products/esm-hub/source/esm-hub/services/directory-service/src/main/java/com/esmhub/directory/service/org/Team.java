package com.esmhub.directory.service.org;

import jakarta.persistence.*;
import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "teams")
public class Team {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "team_id") private Long id;
    @Column(name = "company_id") private long companyId;
    private String name;
    @Column(name = "support_level") private int supportLevel;
    @Column(name = "manager_user_id") private Long managerUserId;
    @Column(name = "is_active") private boolean active = true;
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "team_members", joinColumns = @JoinColumn(name = "team_id"))
    @Column(name = "user_id")
    private Set<Long> memberIds = new HashSet<>();

    protected Team() {}
    public Team(long companyId) { this.companyId = companyId; }

    public void update(String name, int supportLevel, Long managerUserId, boolean active) {
        this.name = name; this.supportLevel = supportLevel; this.managerUserId = managerUserId; this.active = active;
    }
    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public int getSupportLevel() { return supportLevel; }
    public Long getManagerUserId() { return managerUserId; }
    public boolean isActive() { return active; }
    public Set<Long> getMemberIds() { return memberIds; }
}
