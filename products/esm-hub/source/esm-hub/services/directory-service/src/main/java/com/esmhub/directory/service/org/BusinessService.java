package com.esmhub.directory.service.org;

import jakarta.persistence.*;

/** A business/IT service of the catalogue master data (owned by a resolver team). */
@Entity
@Table(name = "services")
public class BusinessService {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "service_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "category_id") private Long categoryId;
    private String name;
    private String description;
    @Column(name = "owning_team_id") private Long owningTeamId;
    @Column(name = "is_active") private boolean active = true;

    protected BusinessService() {}
    public BusinessService(long companyId) { this.companyId = companyId; }

    public void update(String name, String description, Long categoryId, Long owningTeamId, boolean active) {
        this.name = name; this.description = description; this.categoryId = categoryId;
        this.owningTeamId = owningTeamId; this.active = active;
    }
    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public Long getCategoryId() { return categoryId; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public Long getOwningTeamId() { return owningTeamId; }
    public boolean isActive() { return active; }
}
