package com.esmhub.audit.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.audit.service.audit.AuditDtos.AuditFilter;
import com.esmhub.audit.service.audit.AuditService;
import com.esmhub.audit.service.audit.AuditStore;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class AuditServiceTest {
    AuditStore store = mock(AuditStore.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    AuditService service = new AuditService(store, audit);
    AuditFilter none = new AuditFilter(null, null, null, null, null, null, null);

    CurrentUser user(long company, String role) { return new CurrentUser(5, company, Set.of(role), Set.of(), "U", "u@x.test"); }

    @Test
    void auditorAndAdminCanSearchScopedToTheirCompany() {
        when(store.find(eq(7L), any(), anyInt(), anyLong())).thenReturn(List.of());
        when(store.count(eq(7L), any())).thenReturn(0L);
        assertThat(service.search(user(7, "AUDITOR"), none, 1, 25).total()).isZero();
        service.search(user(7, "ADMIN"), none, 1, 25);
        verify(store, times(2)).find(eq(7L), any(), eq(25), eq(0L));
    }

    @Test
    void otherRolesAreForbidden() {
        for (String r : List.of("EMPLOYEE", "SERVICE_MANAGER", "ASSET_MANAGER", "KNOWLEDGE_EDITOR")) {
            assertThatThrownBy(() -> service.search(user(1, r), none, 1, 25)).isInstanceOf(ForbiddenException.class);
            assertThatThrownBy(() -> service.export(user(1, r), none)).isInstanceOf(ForbiddenException.class);
        }
        verifyNoInteractions(store, audit);
    }

    @Test
    void pageSizeIsValidated() {
        assertThatThrownBy(() -> service.search(user(1, "AUDITOR"), none, 0, 25)).isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> service.search(user(1, "AUDITOR"), none, 1, 201)).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void exportIsAuditedAndReturnsCsv() {
        when(store.find(eq(1L), any(), anyInt(), anyLong())).thenReturn(List.of());
        var res = service.export(user(1, "AUDITOR"), new AuditFilter(null, "ASSET", null, null, null, null, null));
        assertThat(res.getHeaders().getContentType().toString()).startsWith("text/csv");
        verify(audit).record(eq("AUDIT"), eq(0), eq("EXPORT"), isNull(), any());
    }
}
