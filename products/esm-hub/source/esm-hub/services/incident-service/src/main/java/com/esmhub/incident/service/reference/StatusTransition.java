package com.esmhub.incident.service.reference;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import java.io.Serializable;

/** Allowed workflow edge (the service layer enforces it). */
@Entity
@Table(name = "status_transitions")
public class StatusTransition {
    @Embeddable
    public record Key(@Column(name = "from_status_id") Integer fromStatusId,
                      @Column(name = "to_status_id") Integer toStatusId) implements Serializable {}

    @EmbeddedId private Key id;

    protected StatusTransition() {}

    public Key getId() { return id; }
}
