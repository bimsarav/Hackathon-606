package com.esmhub.incident.service.sla;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.incident.Incident;
import com.esmhub.incident.service.reference.BusinessCalendar;
import com.esmhub.incident.service.reference.BusinessCalendarRepository;
import com.esmhub.incident.service.reference.Priority;
import com.esmhub.incident.service.reference.PriorityRepository;
import com.esmhub.incident.service.reference.SlaPolicy;
import com.esmhub.incident.service.reference.SlaPolicyRepository;
import com.esmhub.incident.service.reference.TimezoneCalendar;
import com.esmhub.incident.service.reference.TimezoneCalendarRepository;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class SlaServiceTest {
    DirectoryLookup directory = mock(DirectoryLookup.class);
    TimezoneCalendarRepository tz = mock(TimezoneCalendarRepository.class);
    BusinessCalendarRepository calendars = mock(BusinessCalendarRepository.class);
    SlaPolicyRepository policies = mock(SlaPolicyRepository.class);
    PriorityRepository priorities = mock(PriorityRepository.class);
    SlaService service = new SlaService(directory, tz, calendars, policies, priorities);

    static BusinessCalendar uae() {
        BusinessCalendar c = new BusinessCalendar("UAE", "Asia/Dubai");
        c.update("UAE", "Asia/Dubai", List.of(new BusinessCalendar.Hours(0, LocalTime.of(8, 0), LocalTime.of(17, 0))), List.of());
        ReflectionTestUtils.setField(c, "id", 7L);
        return c;
    }

    static Incident incident(int priority, Long serviceId, Instant created) {
        return new Incident(1L, 1L, "t", "d", 5L, serviceId, null, priority, 1, null, "PORTAL", created);
    }

    @Test
    void calendarFollowsTheRequestersOfficeTimezone() {
        when(directory.timezoneOf(5L)).thenReturn("Asia/Dubai");
        when(tz.findById("Asia/Dubai")).thenReturn(Optional.of(new TimezoneCalendar("Asia/Dubai", 7L)));
        when(calendars.findById(7L)).thenReturn(Optional.of(uae()));
        SlaEngine.Calendar cal = service.calendarForUser(5L);
        assertThat(cal.zone().getId()).isEqualTo("Asia/Dubai");
        assertThat(cal.hours()).hasSize(1);
    }

    @Test
    void unknownOfficeFallsBackToFirstCalendarThenTwentyFourSeven() {
        when(calendars.findFirstByOrderById()).thenReturn(Optional.of(uae()));
        assertThat(service.calendarForUser(5L).zone().getId()).isEqualTo("Asia/Dubai");
        when(calendars.findFirstByOrderById()).thenReturn(Optional.empty());
        assertThat(service.calendarForUser(5L)).isSameAs(SlaEngine.TWENTY_FOUR_SEVEN);
    }

    @Test
    void policyWithoutWorkingHoursFallsBackToTwentyFourSeven() {
        BusinessCalendar empty = new BusinessCalendar("Empty", "UTC");
        when(calendars.findFirstByOrderById()).thenReturn(Optional.of(empty));
        assertThat(service.calendarForUser(5L)).isSameAs(SlaEngine.TWENTY_FOUR_SEVEN);
    }

    @Test
    void selectsTheFirstCandidate() {
        SlaPolicy specific = new SlaPolicy(1L, "svc", 2, 9L, true, 10, 100, LocalDate.of(2026, 1, 1), 2);
        SlaPolicy general = new SlaPolicy(null, "gen", 2, null, true, 30, 480, LocalDate.of(2026, 1, 1), 1);
        when(policies.candidates(1L, 2, 9L, LocalDate.of(2026, 5, 1))).thenReturn(List.of(specific, general));
        assertThat(service.selectPolicy(1L, 2, 9L, LocalDate.of(2026, 5, 1))).containsSame(specific);
    }

    @Test
    void targetsComeFromThePolicyElseFromThePriority() {
        SlaPolicy pol = new SlaPolicy(null, "gen", 2, null, false, 30, 480, LocalDate.of(2026, 1, 1), 1);
        Incident withPolicy = incident(2, null, Instant.parse("2026-11-16T05:00:00Z"));
        withPolicy.setSlaId(4L);
        when(policies.findById(4L)).thenReturn(Optional.of(pol));
        assertThat(service.targetsFor(withPolicy)).isEqualTo(new SlaEngine.Targets(30, 480, false));

        Incident noPolicy = incident(3, null, Instant.parse("2026-11-16T05:00:00Z"));
        when(priorities.findById(3)).thenReturn(Optional.of(new Priority(3, "P3", 240, 2880)));
        assertThat(service.targetsFor(noPolicy)).isEqualTo(new SlaEngine.Targets(240, 2880, true));
    }

    @Test
    void applySetsPolicyAndBusinessHoursDueDates() {
        SlaPolicy pol = new SlaPolicy(null, "gen", 2, null, true, 30, 480, LocalDate.of(2026, 1, 1), 1);
        ReflectionTestUtils.setField(pol, "id", 4L);
        when(policies.candidates(anyLong(), anyInt(), any(), any())).thenReturn(List.of(pol));
        when(policies.findById(4L)).thenReturn(Optional.of(pol));
        when(directory.timezoneOf(5L)).thenReturn("Asia/Dubai");
        when(tz.findById("Asia/Dubai")).thenReturn(Optional.of(new TimezoneCalendar("Asia/Dubai", 7L)));
        when(calendars.findById(7L)).thenReturn(Optional.of(uae()));
        Incident inc = incident(2, null, Instant.parse("2026-11-16T05:00:00Z")); // Mon 09:00 Dubai
        service.apply(inc);
        assertThat(inc.getSlaId()).isEqualTo(4L);
        assertThat(inc.getResponseDueAt()).isEqualTo(Instant.parse("2026-11-16T05:30:00Z"));
        assertThat(inc.getDueAt()).isEqualTo(Instant.parse("2026-11-16T13:00:00Z")); // 480 min from 09:00 = 17:00 Dubai
    }
}
