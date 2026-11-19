package com.esmhub.incident.service.sla;

import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.reference.BusinessCalendar;
import com.esmhub.incident.service.reference.BusinessCalendarRepository;
import com.esmhub.incident.service.reference.Priority;
import com.esmhub.incident.service.reference.PriorityRepository;
import com.esmhub.incident.service.reference.SlaPolicy;
import com.esmhub.incident.service.reference.SlaPolicyRepository;
import com.esmhub.incident.service.reference.TimezoneCalendarRepository;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.EnumMap;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/** Connects the pure {@link SlaEngine} to configuration: policy selection, calendars by office timezone. */
@Service
public class SlaService {
    private final DirectoryLookup directory;
    private final TimezoneCalendarRepository tzCalendars;
    private final BusinessCalendarRepository calendars;
    private final SlaPolicyRepository policies;
    private final PriorityRepository priorities;

    public SlaService(DirectoryLookup directory, TimezoneCalendarRepository tzCalendars, BusinessCalendarRepository calendars,
                      SlaPolicyRepository policies, PriorityRepository priorities) {
        this.directory = directory;
        this.tzCalendars = tzCalendars;
        this.calendars = calendars;
        this.policies = policies;
        this.priorities = priorities;
    }

    public static SlaEngine.Calendar toEngine(BusinessCalendar c) {
        Map<DayOfWeek, SlaEngine.WorkingHours> hours = new EnumMap<>(DayOfWeek.class);
        for (BusinessCalendar.Hours h : c.getHours()) {
            hours.put(DayOfWeek.of(h.weekday() + 1), new SlaEngine.WorkingHours(h.startTime(), h.endTime()));
        }
        ZoneId zone;
        try {
            zone = ZoneId.of(c.getTimezone());
        } catch (RuntimeException e) {
            zone = ZoneOffset.UTC;
        }
        return new SlaEngine.Calendar(zone, hours,
                c.getHolidays().stream().map(BusinessCalendar.Holiday::holidayDate).collect(Collectors.toSet()));
    }

    /** The requester's office calendar (via its timezone); the first calendar as fallback; 24/7 when none is set up. */
    public SlaEngine.Calendar calendarForUser(Long userId) {
        String tz = directory.timezoneOf(userId);
        Optional<BusinessCalendar> cal = Optional.ofNullable(tz).flatMap(tzCalendars::findById)
                .flatMap(m -> calendars.findById(m.getCalendarId()));
        if (cal.isEmpty()) cal = calendars.findFirstByOrderById();
        return cal.filter(c -> !c.getHours().isEmpty()).map(SlaService::toEngine).orElse(SlaEngine.TWENTY_FOUR_SEVEN);
    }

    /** The most specific active policy: service + priority before priority only; newest version wins. */
    public Optional<SlaPolicy> selectPolicy(long companyId, int priorityId, Long serviceId, LocalDate onDate) {
        return policies.candidates(companyId, priorityId, serviceId, onDate).stream().findFirst();
    }

    public SlaEngine.Targets targetsFor(Incident inc) {
        Optional<SlaPolicy> pol = Optional.ofNullable(inc.getSlaId()).flatMap(policies::findById);
        if (pol.isPresent()) {
            SlaPolicy p = pol.get();
            return new SlaEngine.Targets(p.getResponseTargetMinutes(), p.getResolutionTargetMinutes(), p.isBusinessHoursOnly());
        }
        Priority p = priorities.findById(inc.getPriorityId()).orElseThrow();
        return new SlaEngine.Targets(p.getResponseMinutes(), p.getResolutionMinutes(), true);
    }

    /** (Re)selects the policy and recomputes both due dates from created_at, including paused time. */
    public void apply(Incident inc) {
        inc.setSlaId(selectPolicy(inc.getCompanyId(), inc.getPriorityId(), inc.getServiceId(),
                inc.getCreatedAt().atZone(ZoneOffset.UTC).toLocalDate()).map(SlaPolicy::getId).orElse(null));
        recompute(inc);
    }

    /** Recomputes due dates with the current policy and paused minutes. */
    public void recompute(Incident inc) {
        SlaEngine.DueDates d = SlaEngine.dueDates(inc.getCreatedAt(), targetsFor(inc), calendarForUser(inc.getRequesterId()),
                inc.getSlaPausedMinutes());
        inc.setDueDates(d.responseDue(), d.resolutionDue());
    }
}
