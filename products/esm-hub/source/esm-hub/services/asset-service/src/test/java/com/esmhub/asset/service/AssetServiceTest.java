package com.esmhub.asset.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;

import com.esmhub.asset.service.asset.Asset;
import com.esmhub.asset.service.asset.AssetAssignment;
import com.esmhub.asset.service.asset.AssetAssignmentRepository;
import com.esmhub.asset.service.asset.AssetRepository;
import com.esmhub.asset.service.asset.AssetService;
import com.esmhub.asset.service.events.AssetEvents;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.ForbiddenException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import java.time.Instant;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class AssetServiceTest {
    AssetRepository assets = mock(AssetRepository.class);
    AssetAssignmentRepository assignments = mock(AssetAssignmentRepository.class);
    DirectoryLookup directory = mock(DirectoryLookup.class);
    AssetEvents events = mock(AssetEvents.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    AssetService service = new AssetService(assets, assignments, directory, events, audit);
    CurrentUser manager = new CurrentUser(1, 1, Set.of("ASSET_MANAGER"), Set.of(), "M", "m@x");
    CurrentUser employee = new CurrentUser(2, 1, Set.of("EMPLOYEE"), Set.of(), "E", "e@x");
    Asset asset;

    @BeforeEach
    void setUp() {
        asset = new Asset(1, "LT-1", "Laptop");
        ReflectionTestUtils.setField(asset, "id", 7L);
        when(assets.findByIdAndCompanyId(7L, 1L)).thenReturn(Optional.of(asset));
        when(assets.saveAndFlush(any())).thenAnswer(i -> i.getArgument(0));
        when(assignments.findByAssetIdOrderByAssignedAtDescIdDesc(anyLong())).thenReturn(java.util.List.of());
    }

    DirUser user(long id, boolean active) {
        DirUser u = mock(DirUser.class);
        when(u.getUserId()).thenReturn(id);
        when(u.isActive()).thenReturn(active);
        when(directory.userInCompany(id, 1L)).thenReturn(Optional.of(u));
        return u;
    }

    @Test
    void assignClosesPreviousAssignmentAndNotifies() {
        user(5, true);
        AssetAssignment open = new AssetAssignment(7, 4, Instant.now().minusSeconds(60), 1L);
        when(assignments.findByAssetIdAndReturnedAtIsNull(7L)).thenReturn(Optional.of(open));
        var view = service.assign(manager, 7, 5);
        assertThat(open.getReturnedAt()).isNotNull();
        assertThat(view.status()).isEqualTo("ASSIGNED");
        assertThat(view.assignedUserId()).isEqualTo(5L);
        verify(events).assigned(asset, 5L);
        verify(audit).record(eq("ASSET"), any(), eq("ASSIGN"), any(), any());
    }

    @Test
    void inactiveUserCannotBeAssigned() {
        user(5, false);
        assertThatThrownBy(() -> service.assign(manager, 7, 5)).isInstanceOf(BusinessRuleException.class);
        verify(assignments, never()).saveAndFlush(any());
    }

    @Test
    void userOutsideCompanyIsNotFound() {
        when(directory.userInCompany(9L, 1L)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.assign(manager, 7, 9)).isInstanceOf(NotFoundException.class);
    }

    @Test
    void repairedAssetCannotBeAssigned() {
        user(5, true);
        asset.setStatus("REPAIR");
        assertThatThrownBy(() -> service.assign(manager, 7, 5)).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void leavingAssignedClosesAssignment() {
        asset.setStatus("ASSIGNED");
        asset.setAssignedUserId(5L);
        AssetAssignment open = new AssetAssignment(7, 5, Instant.now().minusSeconds(60), 1L);
        when(assignments.findByAssetIdAndReturnedAtIsNull(7L)).thenReturn(Optional.of(open));
        var view = service.changeStatus(manager, 7, "REPAIR");
        assertThat(open.getReturnedAt()).isNotNull();
        assertThat(view.assignedUserId()).isNull();
        assertThat(view.status()).isEqualTo("REPAIR");
    }

    @Test
    void statusCannotJumpToAssignedOrFromRetired() {
        assertThatThrownBy(() -> service.changeStatus(manager, 7, "ASSIGNED")).isInstanceOf(BusinessRuleException.class);
        asset.setStatus("RETIRED");
        assertThatThrownBy(() -> service.changeStatus(manager, 7, "IN_STOCK")).isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void onlyAssetManagersMutate() {
        assertThatThrownBy(() -> service.changeStatus(employee, 7, "LOST")).isInstanceOf(ForbiddenException.class);
        assertThatThrownBy(() -> service.assign(employee, 7, 5)).isInstanceOf(ForbiddenException.class);
    }

    @Test
    void employeeCannotSeeSomeoneElsesAsset() {
        asset.setAssignedUserId(99L);
        assertThatThrownBy(() -> service.get(employee, 7)).isInstanceOf(NotFoundException.class);
        asset.setAssignedUserId(2L);
        assertThat(service.get(employee, 7).assetId()).isEqualTo(7L);
    }
}
