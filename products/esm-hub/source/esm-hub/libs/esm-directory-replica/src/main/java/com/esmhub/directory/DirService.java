package com.esmhub.directory;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Replica of a business service from the service catalogue master data. */
@Entity
@Table(name = "dir_services")
public class DirService {
    @Id @Column(name = "service_id") private Long serviceId;
    @Column(name = "company_id") private long companyId;
    private String name;
    @Column(name = "category_id") private Long categoryId;
    @Column(name = "category_name") private String categoryName;
    @Column(name = "owning_team_id") private Long owningTeamId;
    private boolean active;

    protected DirService() {}

    public DirService(Long serviceId) { this.serviceId = serviceId; }

    void apply(com.esmhub.common.contracts.DirectoryContracts.ServiceSnapshot s) {
        companyId = s.companyId(); name = s.name(); categoryId = s.categoryId(); categoryName = s.categoryName();
        owningTeamId = s.owningTeamId(); active = s.active();
    }

    public Long getServiceId() { return serviceId; }
    public long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public Long getCategoryId() { return categoryId; }
    public String getCategoryName() { return categoryName; }
    public Long getOwningTeamId() { return owningTeamId; }
    public boolean isActive() { return active; }
}
