package com.esmhub.incident.service.admin;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;

public final class AdminDtos {
    private AdminDtos() {}

    public record PriorityIn(@Min(1) @Max(100000) int responseMinutes, @Min(1) @Max(1000000) int resolutionMinutes) {}

    public record PriorityView(int id, String name, int responseMinutes, int resolutionMinutes) {}

    public record SlaIn(@NotBlank @Size(min = 2, max = 100) String name, @Min(1) @Max(4) int priorityId, Long serviceId,
                        Boolean businessHoursOnly, @Min(1) int responseTargetMinutes, @Min(1) int resolutionTargetMinutes,
                        @NotNull LocalDate effectiveFrom) {}

    public record SlaView(long id, Long companyId, String name, int priorityId, Long serviceId, boolean businessHoursOnly,
                          int responseTargetMinutes, int resolutionTargetMinutes, LocalDate effectiveFrom, LocalDate effectiveTo,
                          int version) {}

    public record HoursIn(@Min(0) @Max(6) int weekday, @NotNull LocalTime startTime, @NotNull LocalTime endTime) {}

    public record HolidayIn(@NotNull LocalDate holidayDate, @NotBlank @Size(min = 2, max = 100) String name) {}

    public record CalendarIn(@NotBlank @Size(min = 2, max = 80) String name, @NotBlank @Size(min = 3, max = 60) String timezone,
                             @NotEmpty List<@Valid HoursIn> hours, List<@Valid HolidayIn> holidays) {}

    public record CalendarView(long id, String name, String timezone, List<HoursIn> hours, List<HolidayIn> holidays) {}

    public record RuleIn(Long serviceId, @Min(1) @Max(4) Integer priorityId, @NotNull Long teamId,
                         @Min(0) @Max(10000) Integer sortOrder, Boolean active) {}

    public record RuleView(long id, Long serviceId, Integer priorityId, long teamId, int sortOrder, boolean active) {}

    public record EscalationIn(@Min(1) @Max(4) Integer priorityId,
                               @NotBlank @Pattern(regexp = "RESPONSE_BREACH|RESOLUTION_AT_RISK|RESOLUTION_BREACH") String trigger,
                               @NotBlank @Size(max = 60) String notifyRole, Boolean notifyAssignee, Boolean active) {}

    public record EscalationView(long id, Integer priorityId, String trigger, String notifyRole, boolean notifyAssignee,
                                 boolean active) {}
}
