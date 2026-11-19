package com.esmhub.incident.service.sla;

import java.time.DayOfWeek;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoField;
import java.time.temporal.TemporalAccessor;
import java.util.EnumMap;
import java.util.Map;
import java.util.Set;

/**
 * Business-hours SLA engine (FR-5, ADR-0006). Pure functions with no database access. A calendar is a timezone,
 * working hours per weekday and a set of holidays (local dates). All instants are UTC.
 */
public final class SlaEngine {
    /** Protects against a calendar with no working hours. */
    static final int MAX_DAYS_SCAN = 3660;

    private SlaEngine() {}

    public record WorkingHours(LocalTime start, LocalTime end) {}

    public record Calendar(ZoneId zone, Map<DayOfWeek, WorkingHours> hours, Set<LocalDate> holidays) {
        public Calendar {
            hours = Map.copyOf(hours);
            holidays = Set.copyOf(holidays);
        }
    }

    public record Targets(int responseMinutes, int resolutionMinutes, boolean businessHours) {}

    public record DueDates(Instant responseDue, Instant resolutionDue) {}

    public static final Calendar TWENTY_FOUR_SEVEN = twentyFourSeven();

    private static Calendar twentyFourSeven() {
        Map<DayOfWeek, WorkingHours> h = new EnumMap<>(DayOfWeek.class);
        for (DayOfWeek d : DayOfWeek.values()) h.put(d, new WorkingHours(LocalTime.MIDNIGHT, LocalTime.MAX));
        return new Calendar(ZoneOffset.UTC, h, Set.of());
    }

    /** Converts a date-time that carries an offset or zone; a naive (local) date-time is rejected. */
    public static Instant aware(TemporalAccessor t) {
        if (t == null || !t.isSupported(ChronoField.INSTANT_SECONDS)) {
            throw new IllegalArgumentException("date-time must be timezone-aware");
        }
        return Instant.from(t);
    }

    /** Working window of one local day, or null when the day is not worked. */
    private static ZonedDateTime[] window(Calendar cal, LocalDate day) {
        WorkingHours h = cal.hours().get(day.getDayOfWeek());
        if (h == null || cal.holidays().contains(day)) return null;
        return new ZonedDateTime[] {ZonedDateTime.of(day, h.start(), cal.zone()), ZonedDateTime.of(day, h.end(), cal.zone())};
    }

    /** The instant {@code minutes} working minutes after {@code start}. */
    public static Instant addBusinessMinutes(Instant start, int minutes, Calendar cal, boolean businessHours) {
        if (start == null) throw new IllegalArgumentException("start is required");
        if (minutes < 0) throw new IllegalArgumentException("minutes must be >= 0");
        if (!businessHours) return start.plus(Duration.ofMinutes(minutes));
        Duration remaining = Duration.ofMinutes(minutes);
        Instant cursor = start;
        LocalDate day = start.atZone(cal.zone()).toLocalDate();
        for (int i = 0; i < MAX_DAYS_SCAN; i++, day = day.plusDays(1)) {
            ZonedDateTime[] w = window(cal, day);
            if (w == null) continue;
            Instant ws = w[0].toInstant(), we = w[1].toInstant();
            if (!we.isAfter(cursor)) continue;
            Instant begin = ws.isAfter(cursor) ? ws : cursor;
            Duration available = Duration.between(begin, we);
            if (remaining.compareTo(available) <= 0) return begin.plus(remaining);
            remaining = remaining.minus(available);
        }
        throw new IllegalArgumentException("calendar has no working time within the scan horizon");
    }

    public static Instant addBusinessMinutes(Instant start, int minutes, Calendar cal) {
        return addBusinessMinutes(start, minutes, cal, true);
    }

    /** Working minutes in [start, end), 0 if end <= start. */
    public static int businessMinutesBetween(Instant start, Instant end, Calendar cal, boolean businessHours) {
        if (start == null || end == null) throw new IllegalArgumentException("start and end are required");
        if (!end.isAfter(start)) return 0;
        if (!businessHours) return (int) Duration.between(start, end).toMinutes();
        Duration total = Duration.ZERO;
        LocalDate day = start.atZone(cal.zone()).toLocalDate();
        for (int i = 0; i < MAX_DAYS_SCAN; i++, day = day.plusDays(1)) {
            ZonedDateTime[] w = window(cal, day);
            if (w == null) {
                if (day.atStartOfDay(cal.zone()).toInstant().isAfter(end)) break;
                continue;
            }
            Instant ws = w[0].toInstant(), we = w[1].toInstant();
            if (!ws.isBefore(end)) break;
            Instant lo = ws.isAfter(start) ? ws : start;
            Instant hi = we.isBefore(end) ? we : end;
            if (hi.isAfter(lo)) total = total.plus(Duration.between(lo, hi));
        }
        return (int) total.toMinutes();
    }

    public static int businessMinutesBetween(Instant start, Instant end, Calendar cal) {
        return businessMinutesBetween(start, end, cal, true);
    }

    /** Response and resolution due dates. Paused business minutes push only the resolution clock (BQ-2). */
    public static DueDates dueDates(Instant createdAt, Targets t, Calendar cal, int pausedMinutes) {
        return new DueDates(addBusinessMinutes(createdAt, t.responseMinutes(), cal, t.businessHours()),
                addBusinessMinutes(createdAt, t.resolutionMinutes() + pausedMinutes, cal, t.businessHours()));
    }

    /** Share of the resolution target used so far (percent), excluding paused time. */
    public static double resolutionProgressPct(Instant createdAt, Instant now, Targets t, Calendar cal, int pausedMinutes) {
        int used = businessMinutesBetween(createdAt, now, cal, t.businessHours()) - pausedMinutes;
        return Math.max(0, used) * 100.0 / Math.max(1, t.resolutionMinutes());
    }
}
