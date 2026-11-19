package com.esmhub.directory.service.org;

import jakarta.persistence.*;

@Entity
@Table(name = "offices")
public class Office {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "office_id") private Long id;
    @Column(name = "company_id") private long companyId;
    private String name;
    private String city;
    private String country;
    private String timezone;

    protected Office() {}
    public Office(long companyId) { this.companyId = companyId; }

    public void update(String name, String city, String country, String timezone) {
        this.name = name; this.city = city; this.country = country; this.timezone = timezone;
    }
    public Long getId() { return id; }
    public long getCompanyId() { return companyId; }
    public String getName() { return name; }
    public String getCity() { return city; }
    public String getCountry() { return country; }
    public String getTimezone() { return timezone; }
}
