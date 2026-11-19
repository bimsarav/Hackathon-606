package com.esmhub.incident.service.reference;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Embeddable;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;

/** Office business-hours calendar (BQ-1, NFR-10): timezone, working hours per weekday (0 = Monday), holidays. */
@Entity
@Table(name = "business_calendars")
public class BusinessCalendar {
    @Embeddable
    public record Hours(@Column(name = "weekday") int weekday, @Column(name = "start_time") LocalTime startTime,
                        @Column(name = "end_time") LocalTime endTime) {}

    @Embeddable
    public record Holiday(@Column(name = "holiday_date") LocalDate holidayDate, @Column(name = "name") String name) {}

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "calendar_id") private Long id;
    private String name;
    private String timezone;
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "calendar_hours", joinColumns = @JoinColumn(name = "calendar_id"))
    private List<Hours> hours = new ArrayList<>();
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "calendar_holidays", joinColumns = @JoinColumn(name = "calendar_id"))
    private List<Holiday> holidays = new ArrayList<>();

    protected BusinessCalendar() {}

    public BusinessCalendar(String name, String timezone) {
        this.name = name;
        this.timezone = timezone;
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public String getTimezone() { return timezone; }
    public List<Hours> getHours() { return List.copyOf(hours); }
    public List<Holiday> getHolidays() { return List.copyOf(holidays); }

    public void update(String name, String timezone, List<Hours> hours, List<Holiday> holidays) {
        this.name = name;
        this.timezone = timezone;
        this.hours.clear();
        this.hours.addAll(hours);
        this.holidays.clear();
        this.holidays.addAll(holidays);
    }
}
