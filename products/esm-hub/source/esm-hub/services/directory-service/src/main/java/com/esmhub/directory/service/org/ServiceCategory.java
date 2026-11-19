package com.esmhub.directory.service.org;

import jakarta.persistence.*;

@Entity
@Table(name = "service_categories")
public class ServiceCategory {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "category_id") private Long id;
    private String name;
    @Column(name = "parent_id") private Long parentId;

    protected ServiceCategory() {}
    public ServiceCategory(String name, Long parentId) { this.name = name; this.parentId = parentId; }
    public Long getId() { return id; }
    public String getName() { return name; }
    public Long getParentId() { return parentId; }
}
