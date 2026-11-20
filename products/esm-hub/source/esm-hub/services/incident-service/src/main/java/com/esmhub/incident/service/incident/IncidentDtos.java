package com.esmhub.incident.service.incident;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;

public final class IncidentDtos {
    private IncidentDtos() {}

    public static final String CHANNELS = "PORTAL|EMAIL|PHONE|CHAT|MONITORING";

    public record CreateIncident(@NotBlank @Size(min = 3, max = 200) String title,
                                 @NotBlank @Size(min = 3, max = 20000) String description,
                                 Long serviceId, Long assetId, @Min(1) @Max(4) Integer priorityId,
                                 @Pattern(regexp = CHANNELS) String channel, Long requesterId) {}

    /** Only the fields that are present (not null) are changed. */
    public record UpdateIncident(@Size(min = 3, max = 200) String title, Long serviceId, Long assetId,
                                 @Min(1) @Max(4) Integer priorityId, Long requesterId) {}

    public record Assign(Long teamId, Long userId) {}

    public record ChangeStatus(@NotBlank @Pattern(regexp = "ASSIGNED|IN_PROGRESS|PENDING_USER|RESOLVED|CLOSED|CANCELLED") String status,
                               @Size(max = 40) String resolutionCode, @Size(max = 5000) String resolutionNotes) {}

    public record Reopen(@NotBlank @Size(min = 3, max = 1000) String reason) {}

    public record AddComment(@NotBlank @Size(max = 10000) String body, Boolean internal) {
        public boolean isInternal() { return Boolean.TRUE.equals(internal); }
    }

    public record AddWorklog(@Min(1) @Max(1440) int minutesSpent, @NotBlank @Size(min = 3, max = 5000) String workDescription) {}

    public record Rate(@NotNull @Min(1) @Max(5) Integer score) {}

    public record CommentView(long id, long authorId, String authorName, String body, boolean internal, Instant createdAt) {}

    public record WorklogView(long id, long userId, String userName, int minutesSpent, String workDescription, Instant loggedAt) {}

    public record EventView(String eventType, String fromValue, String toValue, Long actorId, Instant occurredAt) {}

    public record ProblemRef(long id, String problemNo, String title, String status, boolean knownError, String workaround) {}

    /** List rows leave the detail fields null (they are omitted from the JSON). */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record IncidentView(long id, String ticketNo, String title, String status, String priority, int priorityId,
                               String channel, Long serviceId, Long assetId, long requesterId, String requesterName,
                               Long assignedTeamId, String teamName, Long assignedUserId, String assigneeName,
                               Instant createdAt, Instant updatedAt, Instant firstResponseAt, Instant resolvedAt,
                               Instant closedAt, Instant responseDueAt, Instant dueAt, boolean slaPaused,
                               boolean responseBreached, boolean resolutionBreached, int reopenedCount,
                               Integer satisfactionScore,
                               String description, String resolutionCode, String resolutionNotes, Integer slaPausedMinutes,
                               List<CommentView> comments, List<WorklogView> worklogs, List<EventView> events,
                               List<ProblemRef> problems, List<String> allowedTransitions, Boolean canWork) {}
}
