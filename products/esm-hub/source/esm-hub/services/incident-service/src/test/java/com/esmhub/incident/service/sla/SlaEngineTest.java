package com.esmhub.incident.service.sla;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.esmhub.incident.service.sla.SlaEngine.Calendar;
import com.esmhub.incident.service.sla.SlaEngine.Targets;
import com.esmhub.incident.service.sla.SlaEngine.WorkingHours;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.EnumMap;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Every case of the legacy test_sla.py (FR-5, BQ-1, BQ-2) plus the edge cases of the Java port. */
class SlaEngineTest {
    static Map<DayOfWeek, WorkingHours> weekdays(LocalTime from, LocalTime to) {
        Map<DayOfWeek, WorkingHours> m = new EnumMap<>(DayOfWeek.class);
        for (DayOfWeek d : DayOfWeek.values()) if (d.getValue() <= 5) m.put(d, new WorkingHours(from, to));
        return m;
    }

    static final Calendar UAE = new Calendar(ZoneId.of("Asia/Dubai"), weekdays(LocalTime.of(8, 0), LocalTime.of(17, 0)),
            Set.of(LocalDate.of(2026, 12, 2), LocalDate.of(2026, 12, 3)));
    static final Calendar UK = new Calendar(ZoneId.of("Europe/London"), weekdays(LocalTime.of(9, 0), LocalTime.of(17, 30)), Set.of());

    static Instant utc(int y, int mo, int d, int h) { return utc(y, mo, d, h, 0); }

    static Instant utc(int y, int mo, int d, int h, int mi) { return Instant.parse(String.format("%04d-%02d-%02dT%02d:%02d:00Z", y, mo, d, h, mi)); }

    @Test
    void withinSameDay() {
        // Mon 2026-11-16 06:00 UTC = 10:00 Dubai, +60 min = 11:00 Dubai = 07:00 UTC
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 11, 16, 6), 60, UAE)).isEqualTo(utc(2026, 11, 16, 7));
    }

    @Test
    void beforeOpeningStartsAtOpening() {
        // 02:00 UTC = 06:00 Dubai, before the 08:00 opening; +15 min = 08:15 Dubai = 04:15 UTC
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 11, 16, 2), 15, UAE)).isEqualTo(utc(2026, 11, 16, 4, 15));
    }

    @Test
    void rollsOverWeekend() {
        // Fri 2026-11-20 16:30 Dubai + 60 min: 30 min on Friday, 30 min on Monday from 08:00 = Mon 08:30 Dubai
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 11, 20, 12, 30), 60, UAE)).isEqualTo(utc(2026, 11, 23, 4, 30));
    }

    @Test
    void skipsHolidays() {
        // Tue 2026-12-01 16:00 Dubai + 120 min: 60 min Tuesday, Wed and Thu are holidays, 60 min Friday = Fri 09:00 Dubai
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 12, 1, 12), 120, UAE)).isEqualTo(utc(2026, 12, 4, 5));
    }

    @Test
    void calendarTimeMode() {
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 11, 21, 23), 120, UAE, false)).isEqualTo(utc(2026, 11, 22, 1));
    }

    @Test
    void dstTransitionLondon() {
        // UK clocks go back on Sun 2026-10-25. Fri 2026-10-23 17:00 BST (16:00 UTC) + 60 min = Mon 09:30 GMT = 09:30 UTC
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 10, 23, 16), 60, UK)).isEqualTo(utc(2026, 10, 26, 9, 30));
    }

    @Test
    void minutesBetweenMatchesAdd() {
        Instant start = utc(2026, 11, 19, 10, 7);
        for (int m : new int[] {0, 1, 59, 540, 541, 2880, 5760}) {
            Instant end = SlaEngine.addBusinessMinutes(start, m, UAE);
            assertThat(SlaEngine.businessMinutesBetween(start, end, UAE)).as("minutes %d", m).isEqualTo(m);
        }
    }

    @Test
    void minutesBetweenOutsideHoursIsZero() {
        // Saturday all day
        assertThat(SlaEngine.businessMinutesBetween(utc(2026, 11, 21, 0), utc(2026, 11, 21, 23), UAE)).isZero();
    }

    @Test
    void dueDatesPauseExtendsResolutionOnly() {
        Targets t = new Targets(30, 480, true);
        Instant created = utc(2026, 11, 16, 5); // Mon 09:00 Dubai
        SlaEngine.DueDates d0 = SlaEngine.dueDates(created, t, UAE, 0);
        SlaEngine.DueDates d1 = SlaEngine.dueDates(created, t, UAE, 60);
        assertThat(d1.responseDue()).isEqualTo(d0.responseDue());
        assertThat(SlaEngine.businessMinutesBetween(d0.resolutionDue(), d1.resolutionDue(), UAE)).isEqualTo(60);
    }

    @Test
    void progressPct() {
        Targets t = new Targets(30, 540, true);
        Instant created = utc(2026, 11, 16, 4); // Mon 08:00 Dubai
        assertThat(SlaEngine.resolutionProgressPct(created, utc(2026, 11, 16, 8, 30), t, UAE, 0)).isCloseTo(50.0, org.assertj.core.data.Offset.offset(0.0001));
    }

    @Test
    void progressExcludesPausedTimeAndNeverGoesNegative() {
        Targets t = new Targets(30, 540, true);
        Instant created = utc(2026, 11, 16, 4);
        assertThat(SlaEngine.resolutionProgressPct(created, utc(2026, 11, 16, 5), t, UAE, 600)).isZero();
    }

    @Test
    void naiveDateTimeRejected() {
        assertThatThrownBy(() -> SlaEngine.aware(java.time.LocalDateTime.of(2026, 1, 1, 0, 0)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(SlaEngine.aware(OffsetDateTime.parse("2026-01-01T00:00:00+04:00"))).isEqualTo(Instant.parse("2025-12-31T20:00:00Z"));
    }

    @Test
    void calendarWithoutHoursThrows() {
        Calendar empty = new Calendar(ZoneId.of("UTC"), Map.of(), Set.of());
        assertThatThrownBy(() -> SlaEngine.addBusinessMinutes(utc(2026, 1, 1, 0), 10, empty)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void negativeMinutesRejected() {
        assertThatThrownBy(() -> SlaEngine.addBusinessMinutes(utc(2026, 1, 1, 0), -1, UAE)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void twentyFourSevenNeverWaits() {
        assertThat(SlaEngine.addBusinessMinutes(utc(2026, 11, 21, 23), 120, SlaEngine.TWENTY_FOUR_SEVEN)).isEqualTo(utc(2026, 11, 22, 1));
    }
}
