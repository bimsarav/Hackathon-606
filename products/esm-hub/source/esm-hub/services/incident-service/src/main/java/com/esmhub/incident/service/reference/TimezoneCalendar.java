package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Maps an office timezone (directory replica) to the business calendar used for its requesters. */
@Entity
@Table(name = "timezone_calendars")
public class TimezoneCalendar {
    @Id private String timezone;
    @Column(name = "calendar_id") private long calendarId;

    protected TimezoneCalendar() {}

    public TimezoneCalendar(String timezone, long calendarId) {
        this.timezone = timezone;
        this.calendarId = calendarId;
    }

    public String getTimezone() { return timezone; }
    public long getCalendarId() { return calendarId; }
    public void setCalendarId(long calendarId) { this.calendarId = calendarId; }
}
