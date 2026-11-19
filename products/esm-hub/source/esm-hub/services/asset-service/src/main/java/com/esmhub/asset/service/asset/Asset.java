package com.esmhub.asset.service.asset;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

@Entity
@Table(name = "assets")
public class Asset {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "asset_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "asset_tag") private String assetTag;
    @Column(name = "asset_type") private String assetType;
    private String manufacturer;
    private String model;
    @Column(name = "serial_number") private String serialNumber;
    @Column(name = "purchase_date") private LocalDate purchaseDate;
    @Column(name = "warranty_end") private LocalDate warrantyEnd;
    @Column(name = "office_id") private Long officeId;
    @Column(name = "assigned_user_id") private Long assignedUserId;
    @Column(name = "asset_status") private String status = AssetRules.IN_STOCK;
    @Column(name = "purchase_cost") private BigDecimal purchaseCost;
    @Column(name = "created_at") private Instant createdAt = Instant.now();
    @Column(name = "updated_at") private Instant updatedAt = Instant.now();

    protected Asset() {}

    public Asset(long companyId, String assetTag, String assetType) {
        this.companyId = companyId; this.assetTag = assetTag; this.assetType = assetType;
    }

    public void touch() { this.updatedAt = Instant.now(); }

    public void setDetails(String manufacturer, String model, String serialNumber, LocalDate purchaseDate,
                           LocalDate warrantyEnd, Long officeId, BigDecimal purchaseCost) {
        this.manufacturer = manufacturer; this.model = model; this.serialNumber = serialNumber;
        this.purchaseDate = purchaseDate; this.warrantyEnd = warrantyEnd; this.officeId = officeId;
        this.purchaseCost = purchaseCost;
    }

    public void setManufacturer(String v) { this.manufacturer = v; }
    public void setModel(String v) { this.model = v; }
    public void setWarrantyEnd(LocalDate v) { this.warrantyEnd = v; }
    public void setOfficeId(Long v) { this.officeId = v; }
    public void setPurchaseCost(BigDecimal v) { this.purchaseCost = v; }
    public void setStatus(String v) { this.status = v; }
    public void setAssignedUserId(Long v) { this.assignedUserId = v; }

    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public String getAssetTag() { return assetTag; }
    public String getAssetType() { return assetType; }
    public String getManufacturer() { return manufacturer; }
    public String getModel() { return model; }
    public String getSerialNumber() { return serialNumber; }
    public LocalDate getPurchaseDate() { return purchaseDate; }
    public LocalDate getWarrantyEnd() { return warrantyEnd; }
    public Long getOfficeId() { return officeId; }
    public Long getAssignedUserId() { return assignedUserId; }
    public String getStatus() { return status; }
    public BigDecimal getPurchaseCost() { return purchaseCost; }
    public Instant getCreatedAt() { return createdAt; }
}
