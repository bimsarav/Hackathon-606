package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;

/** Versioned SLA policy. A new version ends the previous one (history kept for existing tickets). */
@Entity
@Table(name = "sla_policies")
public class SlaPolicy {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "sla_id") private Long id;
    @Column(name = "company_id") private Long companyId;
    private String name;
    @Column(name = "priority_id") private int priorityId;
    @Column(name = "service_id") private Long serviceId;
    @Column(name = "business_hours_only") private boolean businessHoursOnly;
    @Column(name = "response_target_minutes") private int responseTargetMinutes;
    @Column(name = "resolution_target_minutes") private int resolutionTargetMinutes;
    @Column(name = "effective_from") private LocalDate effectiveFrom;
    @Column(name = "effective_to") private LocalDate effectiveTo;
    private int version;

    protected SlaPolicy() {}

    public SlaPolicy(Long companyId, String name, int priorityId, Long serviceId, boolean businessHoursOnly,
                     int responseTargetMinutes, int resolutionTargetMinutes, LocalDate effectiveFrom, int version) {
        this.companyId = companyId;
        this.name = name;
        this.priorityId = priorityId;
        this.serviceId = serviceId;
        this.businessHoursOnly = businessHoursOnly;
        this.responseTargetMinutes = responseTargetMinutes;
        this.resolutionTargetMinutes = resolutionTargetMinutes;
        this.effectiveFrom = effectiveFrom;
        this.version = version;
    }

    public Long getId() { return id; }
    public Long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public int getPriorityId() { return priorityId; }
    public Long getServiceId() { return serviceId; }
    public boolean isBusinessHoursOnly() { return businessHoursOnly; }
    public int getResponseTargetMinutes() { return responseTargetMinutes; }
    public int getResolutionTargetMinutes() { return resolutionTargetMinutes; }
    public LocalDate getEffectiveFrom() { return effectiveFrom; }
    public LocalDate getEffectiveTo() { return effectiveTo; }
    public int getVersion() { return version; }
    public void endOn(LocalDate date) { this.effectiveTo = date; }
}
