package com.esmhub.request.service.catalogue;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "catalogue_items")
public class CatalogueItem {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "item_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "service_id") private long serviceId;
    private String name;
    private String description;
    @Column(name = "base_cost") private BigDecimal baseCost = BigDecimal.ZERO;
    @Column(name = "fulfilment_team_id") private Long fulfilmentTeamId;
    private boolean active = true;
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "approval_steps", joinColumns = @JoinColumn(name = "item_id"))
    private List<ApprovalStep> steps = new ArrayList<>();

    protected CatalogueItem() {}
    public CatalogueItem(long companyId) { this.companyId = companyId; }

    public void apply(long serviceId, String name, String description, BigDecimal baseCost, Long fulfilmentTeamId,
                      boolean active, List<ApprovalStep> newSteps) {
        this.serviceId = serviceId; this.name = name; this.description = description; this.baseCost = baseCost;
        this.fulfilmentTeamId = fulfilmentTeamId; this.active = active;
        steps.clear();
        steps.addAll(newSteps);
    }

    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public long getServiceId() { return serviceId; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public BigDecimal getBaseCost() { return baseCost; }
    public Long getFulfilmentTeamId() { return fulfilmentTeamId; }
    public boolean isActive() { return active; }
    public List<ApprovalStep> getSteps() { return steps; }
}
