package com.esmhub.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.CsvWriter;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.PageResponse;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Sort;

class CommonUnitTest {

    @Test
    void csvNeutralisesFormulaInjectionAndQuotes() {
        assertThat(CsvWriter.cell("=HYPERLINK(\"x\")")).isEqualTo("\"'=HYPERLINK(\"\"x\"\")\"");
        assertThat(CsvWriter.cell("-1")).isEqualTo("'-1");
        assertThat(CsvWriter.cell("a,b")).isEqualTo("\"a,b\"");
        assertThat(CsvWriter.cell(null)).isEmpty();
        assertThat(CsvWriter.cell("plain")).isEqualTo("plain");
    }

    @Test
    void currentUserRoleChecks() {
        CurrentUser u = new CurrentUser(3, 1, Set.of("TECHNICIAN"), Set.of(1L), "Maya", "m@example.test");
        assertThat(u.has(Role.TECHNICIAN)).isTrue();
        assertThat(u.has(Role.ADMIN, Role.AUDITOR)).isFalse();
        assertThat(u.isStaff()).isTrue();
        assertThat(u.inTeam(1L)).isTrue();
        assertThat(u.inTeam(null)).isFalse();
        assertThatThrownBy(() -> u.require(Role.ADMIN)).isInstanceOf(ForbiddenException.class);
    }

    @Test
    void pageableValidation() {
        assertThat(PageResponse.pageable(2, 25, Sort.unsorted()).getPageNumber()).isEqualTo(1);
        assertThatThrownBy(() -> PageResponse.pageable(0, 25, Sort.unsorted())).isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> PageResponse.pageable(1, 201, Sort.unsorted())).isInstanceOf(BusinessRuleException.class);
    }
}
