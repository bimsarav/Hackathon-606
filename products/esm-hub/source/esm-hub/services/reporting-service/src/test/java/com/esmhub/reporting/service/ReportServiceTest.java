package com.esmhub.reporting.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.reporting.service.reports.ReportService;
import java.time.LocalDate;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;

class ReportServiceTest {
    NamedParameterJdbcTemplate jdbc = mock(NamedParameterJdbcTemplate.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    ReportService service = new ReportService(jdbc, audit);

    static CurrentUser user(String role) {
        return new CurrentUser(1, 1, Set.of(role), Set.of(), "U", "u@example.test");
    }

    @Test
    void employeesAndTechniciansAreDeniedEveryReport() {
        for (String role : new String[] {"EMPLOYEE", "TECHNICIAN"}) {
            CurrentUser me = user(role);
            assertThatThrownBy(() -> service.summary(me, null, null)).isInstanceOf(ForbiddenException.class);
            assertThatThrownBy(() -> service.backlogAgeing(me)).isInstanceOf(ForbiddenException.class);
            assertThatThrownBy(() -> service.problems(me)).isInstanceOf(ForbiddenException.class);
            assertThatThrownBy(() -> service.export(me, "workload", "month", null, null)).isInstanceOf(ForbiddenException.class);
        }
        verifyNoInteractions(jdbc, audit);
    }

    @Test
    void unknownVolumeDimensionIsRejectedBeforeAnyQuery() {
        assertThatThrownBy(() -> service.incidentVolume(user("ADMIN"), "colour", null, null)).isInstanceOf(BusinessRuleException.class);
        verifyNoInteractions(jdbc);
    }

    @Test
    void sinceAfterUntilIsRejected() {
        assertThatThrownBy(() -> service.slaCompliance(user("ADMIN"), LocalDate.of(2026, 3, 1), LocalDate.of(2026, 2, 1)))
                .isInstanceOf(BusinessRuleException.class);
        verifyNoInteractions(jdbc);
    }

    @Test
    void unknownExportIsNotFoundAndNotAudited() {
        assertThatThrownBy(() -> service.export(user("ADMIN"), "secrets", "month", null, null)).isInstanceOf(NotFoundException.class);
        verifyNoInteractions(audit);
    }
}
