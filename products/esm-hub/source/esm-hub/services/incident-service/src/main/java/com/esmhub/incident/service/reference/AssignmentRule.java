package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** FR-6: routes new incidents to a team by service and/or priority (first active match by sort order). */
@Entity
@Table(name = "assignment_rules")
public class AssignmentRule {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "rule_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "service_id") private Long serviceId;
    @Column(name = "priority_id") private Integer priorityId;
    @Column(name = "team_id") private long teamId;
    @Column(name = "sort_order") private int sortOrder;
    private boolean active;

    protected AssignmentRule() {}

    public AssignmentRule(long companyId) { this.companyId = companyId; }

    public void update(Long serviceId, Integer priorityId, long teamId, int sortOrder, boolean active) {
        this.serviceId = serviceId;
        this.priorityId = priorityId;
        this.teamId = teamId;
        this.sortOrder = sortOrder;
        this.active = active;
    }

    public boolean matches(Long service, int priority) {
        return active && (serviceId == null || serviceId.equals(service)) && (priorityId == null || priorityId == priority);
    }

    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public Long getServiceId() { return serviceId; }
    public Integer getPriorityId() { return priorityId; }
    public long getTeamId() { return teamId; }
    public int getSortOrder() { return sortOrder; }
    public boolean isActive() { return active; }
}
