package com.esmhub.incident.service.problem;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.PostLoad;
import jakarta.persistence.PostPersist;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import java.time.Instant;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.Persistable;

/** Problem record (FR-7) with its linked incidents (incident_problem_links). */
@Entity
@Table(name = "problems")
public class Problem implements Persistable<Long> {
    public static final String OPEN = "OPEN", INVESTIGATING = "INVESTIGATING", KNOWN_ERROR = "KNOWN_ERROR",
            RESOLVED = "RESOLVED", CLOSED = "CLOSED";

    @Id @Column(name = "problem_id") private Long id;
    @Column(name = "company_id") private long companyId;
    @Column(name = "problem_no") private String problemNo;
    private String title;
    private String description;
    private String status;
    @Column(name = "root_cause") private String rootCause;
    private String workaround;
    @Column(name = "known_error") private boolean knownError;
    @Column(name = "owner_team_id") private Long ownerTeamId;
    @Column(name = "created_at") private Instant createdAt;
    @Column(name = "updated_at") private Instant updatedAt;
    @Column(name = "resolved_at") private Instant resolvedAt;
    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "incident_problem_links", joinColumns = @JoinColumn(name = "problem_id"))
    @Column(name = "incident_id")
    private Set<Long> incidentIds = new HashSet<>();
    @Transient private boolean isNew;

    protected Problem() {}

    public Problem(long id, long companyId, String title, String description, Long ownerTeamId, Instant now) {
        this.id = id;
        this.companyId = companyId;
        this.problemNo = String.format("PRB-%05d", id);
        this.title = title;
        this.description = description;
        this.status = OPEN;
        this.ownerTeamId = ownerTeamId;
        this.createdAt = now;
        this.updatedAt = now;
        this.isNew = true;
    }

    @Override public Long getId() { return id; }
    @Override public boolean isNew() { return isNew; }
    @PostLoad @PostPersist void markNotNew() { isNew = false; }

    public Map<String, Object> auditState() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("title", title);
        m.put("status", status);
        m.put("knownError", knownError);
        m.put("ownerTeamId", ownerTeamId);
        m.put("hasRootCause", rootCause != null && !rootCause.isBlank());
        m.put("hasWorkaround", workaround != null && !workaround.isBlank());
        m.put("resolvedAt", resolvedAt == null ? null : resolvedAt.toString());
        return m;
    }

    public long getCompanyId() { return companyId; }
    public String getProblemNo() { return problemNo; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getRootCause() { return rootCause; }
    public void setRootCause(String rootCause) { this.rootCause = rootCause; }
    public String getWorkaround() { return workaround; }
    public void setWorkaround(String workaround) { this.workaround = workaround; }
    public boolean isKnownError() { return knownError; }
    public void setKnownError(boolean knownError) { this.knownError = knownError; }
    public Long getOwnerTeamId() { return ownerTeamId; }
    public void setOwnerTeamId(Long ownerTeamId) { this.ownerTeamId = ownerTeamId; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void touch(Instant now) { this.updatedAt = now; }
    public Instant getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(Instant resolvedAt) { this.resolvedAt = resolvedAt; }
    public Set<Long> getIncidentIds() { return Set.copyOf(incidentIds); }
    public boolean link(long incidentId) { return incidentIds.add(incidentId); }
    public boolean unlink(long incidentId) { return incidentIds.remove(incidentId); }
}
