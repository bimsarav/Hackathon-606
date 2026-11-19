package com.esmhub.directory.service.org;

import jakarta.persistence.*;

@Entity
@Table(name = "companies")
public class Company {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "company_id") private Long id;
    private String name;
    private String code;

    protected Company() {}
    public Long getId() { return id; }
    public String getName() { return name; }
    public String getCode() { return code; }
}
