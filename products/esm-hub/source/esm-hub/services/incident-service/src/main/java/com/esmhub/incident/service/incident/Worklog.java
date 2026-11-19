package com.esmhub.incident.service.incident;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "worklogs")
public class Worklog {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @Column(name = "worklog_id") private Long id;
    @Column(name = "incident_id") private long incidentId;
    @Column(name = "user_id") private long userId;
    @Column(name = "minutes_spent") private int minutesSpent;
    @Column(name = "work_description") private String workDescription;
    @Column(name = "logged_at") private Instant loggedAt;

    protected Worklog() {}

    public Worklog(long incidentId, long userId, int minutesSpent, String workDescription, Instant loggedAt) {
        this.incidentId = incidentId;
        this.userId = userId;
        this.minutesSpent = minutesSpent;
        this.workDescription = workDescription;
        this.loggedAt = loggedAt;
    }

    public Long getId() { return id; }
    public long getIncidentId() { return incidentId; }
    public long getUserId() { return userId; }
    public int getMinutesSpent() { return minutesSpent; }
    public String getWorkDescription() { return workDescription; }
    public Instant getLoggedAt() { return loggedAt; }
}
