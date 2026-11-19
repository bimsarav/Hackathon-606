package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "priorities")
public class Priority {
    @Id @Column(name = "priority_id") private Integer id;
    private String name;
    @Column(name = "response_minutes") private int responseMinutes;
    @Column(name = "resolution_minutes") private int resolutionMinutes;

    protected Priority() {}

    public Priority(int id, String name, int responseMinutes, int resolutionMinutes) {
        this.id = id;
        this.name = name;
        this.responseMinutes = responseMinutes;
        this.resolutionMinutes = resolutionMinutes;
    }

    public Integer getId() { return id; }
    public String getName() { return name; }
    public int getResponseMinutes() { return responseMinutes; }
    public int getResolutionMinutes() { return resolutionMinutes; }

    public void setTargets(int response, int resolution) {
        this.responseMinutes = response;
        this.resolutionMinutes = resolution;
    }
}
