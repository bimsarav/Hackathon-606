package com.esmhub.reporting.service.reports;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

/** Reporting window [since, until): defaults are until = tomorrow and since = until - 365 days (as in the Python product). */
public record ReportRange(LocalDate since, LocalDate until) {
    public static ReportRange of(LocalDate since, LocalDate until, LocalDate today) {
        LocalDate u = until != null ? until : today.plusDays(1);
        LocalDate s = since != null ? since : u.minusDays(365);
        return new ReportRange(s, u);
    }

    public OffsetDateTime from() { return since.atStartOfDay().atOffset(ZoneOffset.UTC); }

    public OffsetDateTime to() { return until.atStartOfDay().atOffset(ZoneOffset.UTC); }
}
