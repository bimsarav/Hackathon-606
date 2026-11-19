package com.esmhub.directory;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Replica of an office (location with IANA timezone). */
@Entity
@Table(name = "dir_offices")
public class DirOffice {
    @Id @Column(name = "office_id") private Long officeId;
    @Column(name = "company_id") private long companyId;
    private String name;
    private String city;
    private String country;
    private String timezone;

    protected DirOffice() {}

    public DirOffice(Long officeId) { this.officeId = officeId; }

    void apply(com.esmhub.common.contracts.DirectoryContracts.OfficeSnapshot s) {
        companyId = s.companyId(); name = s.name(); city = s.city(); country = s.country(); timezone = s.timezone();
    }

    public Long getOfficeId() { return officeId; }
    public long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public String getCity() { return city; }
    public String getCountry() { return country; }
    public String getTimezone() { return timezone; }
}
