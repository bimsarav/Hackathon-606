package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "ticket_statuses")
public class TicketStatus {
    public static final String NEW = "NEW", ASSIGNED = "ASSIGNED", IN_PROGRESS = "IN_PROGRESS",
            PENDING_USER = "PENDING_USER", RESOLVED = "RESOLVED", CLOSED = "CLOSED", CANCELLED = "CANCELLED";

    @Id @Column(name = "status_id") private Integer id;
    private String name;
    @Column(name = "is_closed") private boolean closed;
    @Column(name = "pauses_sla") private boolean pausesSla;

    protected TicketStatus() {}

    public TicketStatus(int id, String name, boolean closed, boolean pausesSla) {
        this.id = id;
        this.name = name;
        this.closed = closed;
        this.pausesSla = pausesSla;
    }

    public Integer getId() { return id; }
    public String getName() { return name; }
    public boolean isClosed() { return closed; }
    public boolean isPausesSla() { return pausesSla; }
}
