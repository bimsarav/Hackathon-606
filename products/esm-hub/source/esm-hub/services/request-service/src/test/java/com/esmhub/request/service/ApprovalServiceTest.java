package com.esmhub.request.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.request.service.approval.ApprovalService;
import com.esmhub.request.service.approval.RequestApproval;
import com.esmhub.request.service.approval.RequestApprovalRepository;
import com.esmhub.request.service.catalogue.ApprovalStep;
import com.esmhub.request.service.catalogue.CatalogueItem;
import com.esmhub.request.service.catalogue.CatalogueItemRepository;
import com.esmhub.request.service.events.RequestEvents;
import com.esmhub.request.service.request.ServiceRequest;
import com.esmhub.request.service.request.ServiceRequestRepository;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.directory.DirectoryLookup;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class ApprovalServiceTest {
    RequestApprovalRepository approvals = mock(RequestApprovalRepository.class);
    ServiceRequestRepository requests = mock(ServiceRequestRepository.class);
    CatalogueItemRepository items = mock(CatalogueItemRepository.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    RequestEvents events = mock(RequestEvents.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    ApprovalService service = new ApprovalService(approvals, requests, items, directory, events, audit);
    ServiceRequest request;

    @BeforeEach
    void setUp() {
        request = new ServiceRequest(1, 3, 10L, 5L, "Laptop", null, new BigDecimal("1200"), 2L, Instant.now());
        ReflectionTestUtils.setField(request, "id", 100L);
        request.setStatus("PENDING_APPROVAL", Instant.now());
        CatalogueItem item = new CatalogueItem(1);
        item.apply(10, "Laptop", null, new BigDecimal("1200"), 2L, true, List.of(
                new ApprovalStep(1, "MANAGER", null, BigDecimal.ZERO), new ApprovalStep(2, "ROLE", "SERVICE_MANAGER", new BigDecimal("1000"))));
        when(items.findById(anyLong())).thenReturn(Optional.of(item));
        when(requests.findById(100L)).thenReturn(Optional.of(request));
        when(directory.userInCompany(anyLong(), anyLong())).thenReturn(Optional.empty());
        when(directory.activeUserIdsWithRole(anyLong(), anyString())).thenReturn(Set.of(20L));
        when(approvals.save(any())).thenAnswer(i -> i.getArguments()[0]);
    }

    RequestApproval pending(int step, Long approver, String role) {
        var a = new RequestApproval(100, step, approver, role, Instant.now());
        ReflectionTestUtils.setField(a, "id", 1L);
        when(approvals.lockById(1L)).thenReturn(Optional.of(a));
        return a;
    }

    @Test
    void approvingNonFinalStepOpensNextStepAndKeepsRequestPending() {
        pending(1, 7L, null);
        service.decide(ApprovalEngineTest.user(7), 1, "APPROVED", "ok");
        assertThat(request.getStatus()).isEqualTo("PENDING_APPROVAL");
        verify(approvals).save(argThat(n -> n.getStepOrder() == 2 && "SERVICE_MANAGER".equals(n.getApproverRole())));
        verify(events).notify(eq("request.approval_requested"), eq(request), eq(Set.of(20L)), anyString(), any(), anyString());
    }

    @Test
    void approvingFinalStepApprovesAndNotifiesRequester() {
        pending(2, null, "SERVICE_MANAGER");
        var a = service.decide(ApprovalEngineTest.user(8, "SERVICE_MANAGER"), 1, "APPROVED", null);
        assertThat(request.getStatus()).isEqualTo("APPROVED");
        assertThat(request.getApprovedAt()).isNotNull();
        assertThat(a.approverId()).isEqualTo(8L);
        verify(events).notify(eq("request.approved"), eq(request), eq(Set.of(3L)), anyString(), any(), anyString());
    }

    @Test
    void rejectionEndsTheChain() {
        pending(1, 7L, null);
        service.decide(ApprovalEngineTest.user(7), 1, "REJECTED", "no budget");
        assertThat(request.getStatus()).isEqualTo("REJECTED");
        verify(events).notify(eq("request.rejected"), eq(request), eq(Set.of(3L)), anyString(), eq("no budget"), anyString());
        verify(approvals, never()).save(any());
    }

    @Test
    void requesterCannotApproveOwnRequest() {
        pending(2, null, "SERVICE_MANAGER");
        assertThatThrownBy(() -> service.decide(ApprovalEngineTest.user(3, "SERVICE_MANAGER"), 1, "APPROVED", null))
                .isInstanceOf(ForbiddenException.class);
    }

    @Test
    void secondDecisionIsAConflict() {
        var a = pending(1, 7L, null);
        a.decide("APPROVED", null, 7, Instant.now());
        assertThatThrownBy(() -> service.decide(ApprovalEngineTest.user(7), 1, "REJECTED", null)).isInstanceOf(ConflictException.class);
    }

    @Test
    void otherCompanyRequestLooksMissing() {
        pending(1, 7L, null);
        assertThatThrownBy(() -> service.decide(new com.esmhub.common.security.CurrentUser(7, 2, Set.of(), Set.of(), "n", "e"), 1, "APPROVED", null))
                .isInstanceOf(com.esmhub.common.web.NotFoundException.class);
    }
}
