package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Who is notified when an SLA trigger fires. notifyRole TEAM_LEAD means the lead of the assigned team. */
@Entity
@Table(name = "escalation_rules")
public class EscalationRule {
    public static final String RESPONSE_BREACH = "RESPONSE_BREACH", RESOLUTION_AT_RISK = "RESOLUTION_AT_RISK",
            RESOLUTION_BREACH = "RESOLUTION_BREACH";

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "rule_id") private Long id;
    @Column(name = "company_id") private Long companyId;
    @Column(name = "priority_id") private Integer priorityId;
    @Column(name = "trigger_type") private String trigger;
    @Column(name = "notify_role") private String notifyRole;
    @Column(name = "notify_assignee") private boolean notifyAssignee;
    private boolean active;

    protected EscalationRule() {}

    public EscalationRule(Long companyId) { this.companyId = companyId; }

    public void update(Integer priorityId, String trigger, String notifyRole, boolean notifyAssignee, boolean active) {
        this.priorityId = priorityId;
        this.trigger = trigger;
        this.notifyRole = notifyRole;
        this.notifyAssignee = notifyAssignee;
        this.active = active;
    }

    public Long getId() { return id; }
    public Long getCompanyId() { return companyId; }
    public Integer getPriorityId() { return priorityId; }
    public String getTrigger() { return trigger; }
    public String getNotifyRole() { return notifyRole; }
    public boolean isNotifyAssignee() { return notifyAssignee; }
    public boolean isActive() { return active; }
}
