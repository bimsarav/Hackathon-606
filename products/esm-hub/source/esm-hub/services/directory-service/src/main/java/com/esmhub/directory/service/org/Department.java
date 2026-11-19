package com.esmhub.directory.service.org;

import jakarta.persistence.*;

@Entity
@Table(name = "departments")
public class Department {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "department_id") private Long id;
    @Column(name = "company_id") private long companyId;
    private String name;
    @Column(name = "cost_centre") private String costCentre;

    protected Department() {}
    public Department(long companyId, String name, String costCentre) {
        this.companyId = companyId; this.name = name; this.costCentre = costCentre;
    }
    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public String getCostCentre() { return costCentre; }
}
