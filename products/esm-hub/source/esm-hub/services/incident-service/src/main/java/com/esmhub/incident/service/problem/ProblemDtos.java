package com.esmhub.incident.service.problem;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;

public final class ProblemDtos {
    private ProblemDtos() {}

    public record CreateProblem(@NotBlank @Size(min = 3, max = 200) String title, @Size(max = 10000) String description,
                                Long ownerTeamId, List<Long> incidentIds) {}

    /** Only fields that are present (not null) are changed. */
    public record UpdateProblem(@Size(min = 3, max = 200) String title, @Size(max = 10000) String description,
                                @Pattern(regexp = "OPEN|INVESTIGATING|KNOWN_ERROR|RESOLVED|CLOSED") String status,
                                @Size(max = 10000) String rootCause, @Size(max = 10000) String workaround, Long ownerTeamId) {}

    public record LinkIncidents(@NotEmpty @Size(max = 200) List<Long> incidentIds) {}

    public record IncidentRef(long id, String ticketNo, String title, String status, String priority, Instant createdAt) {}

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record ProblemView(long id, String problemNo, String title, String description, String status, String rootCause,
                              String workaround, boolean knownError, Long ownerTeamId, Instant createdAt, Instant updatedAt,
                              Instant resolvedAt, int incidentCount, List<IncidentRef> incidents) {}
}
