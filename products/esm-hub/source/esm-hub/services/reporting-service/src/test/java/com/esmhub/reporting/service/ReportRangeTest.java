package com.esmhub.reporting.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.esmhub.reporting.service.reports.ReportRange;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import org.junit.jupiter.api.Test;

class ReportRangeTest {
    static final LocalDate TODAY = LocalDate.of(2026, 5, 10);

    @Test
    void defaultsToLastYearUntilTomorrow() {
        ReportRange r = ReportRange.of(null, null, TODAY);
        assertThat(r.until()).isEqualTo(LocalDate.of(2026, 5, 11));
        assertThat(r.since()).isEqualTo(LocalDate.of(2026, 5, 11).minusDays(365));
    }

    @Test
    void explicitBoundsAreKept() {
        ReportRange r = ReportRange.of(LocalDate.of(2026, 1, 1), LocalDate.of(2026, 2, 1), TODAY);
        assertThat(r.since()).isEqualTo(LocalDate.of(2026, 1, 1));
        assertThat(r.until()).isEqualTo(LocalDate.of(2026, 2, 1));
    }

    @Test
    void sinceDefaultsRelativeToExplicitUntil() {
        ReportRange r = ReportRange.of(null, LocalDate.of(2026, 2, 1), TODAY);
        assertThat(r.since()).isEqualTo(LocalDate.of(2026, 2, 1).minusDays(365));
    }

    @Test
    void boundsAreUtcMidnight() {
        ReportRange r = ReportRange.of(LocalDate.of(2026, 1, 1), LocalDate.of(2026, 2, 1), TODAY);
        assertThat(r.from()).isEqualTo(OffsetDateTime.parse("2026-01-01T00:00:00Z"));
        assertThat(r.to()).isEqualTo(OffsetDateTime.parse("2026-02-01T00:00:00Z"));
    }
}
