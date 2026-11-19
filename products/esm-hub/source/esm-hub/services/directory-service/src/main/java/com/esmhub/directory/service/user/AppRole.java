package com.esmhub.directory.service.user;

import jakarta.persistence.*;

@Entity
@Table(name = "roles")
public class AppRole {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "role_id") private Long id;
    @Column(name = "role_name") private String name;
    private String description;

    protected AppRole() {}
    public Long getId() { return id; }
    public String getName() { return name; }
}
