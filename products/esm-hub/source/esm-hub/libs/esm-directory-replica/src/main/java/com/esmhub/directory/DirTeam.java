package com.esmhub.directory;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Table;
import java.util.HashSet;
import java.util.Set;

/** Replica of a resolver team and its members. */
@Entity
@Table(name = "dir_teams")
public class DirTeam {
    @Id @Column(name = "team_id") private Long teamId;
    @Column(name = "company_id") private long companyId;
    private String name;
    @Column(name = "support_level") private int supportLevel;
    @Column(name = "manager_user_id") private Long managerUserId;
    private boolean active;
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "dir_team_members", joinColumns = @JoinColumn(name = "team_id"))
    @Column(name = "user_id")
    private Set<Long> memberIds = new HashSet<>();

    protected DirTeam() {}

    public DirTeam(Long teamId) { this.teamId = teamId; }

    void apply(com.esmhub.common.contracts.DirectoryContracts.TeamSnapshot s) {
        companyId = s.companyId(); name = s.name(); supportLevel = s.supportLevel(); managerUserId = s.managerUserId();
        active = s.active(); memberIds.clear();
        if (s.memberIds() != null) memberIds.addAll(s.memberIds());
    }

    public Long getTeamId() { return teamId; }
    public long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public int getSupportLevel() { return supportLevel; }
    public Long getManagerUserId() { return managerUserId; }
    public boolean isActive() { return active; }
    public Set<Long> getMemberIds() { return Set.copyOf(memberIds); }
}
