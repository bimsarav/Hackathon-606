package com.esmhub.request.service.catalogue;

import com.esmhub.request.service.catalogue.CatalogueDtos.*;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirService;
import com.esmhub.directory.DirectoryLookup;
import java.math.BigDecimal;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CatalogueService {
    private final CatalogueItemRepository items;
    private final DirectoryLookup directory;
    private final AuditPublisher audit;

    public CatalogueService(CatalogueItemRepository items, DirectoryLookup directory, AuditPublisher audit) {
        this.items = items;
        this.directory = directory;
        this.audit = audit;
    }

    ItemView view(CatalogueItem it) {
        String svc = directory.service(it.getServiceId()).map(DirService::getName).orElse(null);
        return new ItemView(it.getId(), it.getServiceId(), svc, it.getName(), it.getDescription(), it.getBaseCost(),
                it.getFulfilmentTeamId(), it.isActive(),
                it.getSteps().stream().sorted(java.util.Comparator.comparingInt(ApprovalStep::getStepOrder))
                        .map(s -> new StepIO(s.getStepOrder(), s.getApproverType(), s.getApproverRole(), s.getMinCost())).toList());
    }

    @Transactional(readOnly = true)
    public List<ItemView> list(CurrentUser me, boolean includeInactive) {
        var list = includeInactive ? items.findByCompanyIdOrderByName(me.companyId())
                : items.findByCompanyIdAndActiveTrueOrderByName(me.companyId());
        return list.stream().map(this::view).toList();
    }

    @Transactional
    public ItemView create(CurrentUser me, ItemIn req) {
        me.require(Role.SERVICE_MANAGER, Role.ADMIN);
        CatalogueItem it = new CatalogueItem(me.companyId());
        apply(me, it, req);
        items.saveAndFlush(it);
        audit.record("CATALOGUE_ITEM", it.getId(), "CREATE", null, snapshot(it));
        return view(it);
    }

    @Transactional
    public ItemView update(CurrentUser me, long id, ItemIn req) {
        me.require(Role.SERVICE_MANAGER, Role.ADMIN);
        CatalogueItem it = items.findById(id).filter(i -> i.getCompanyId() == me.companyId())
                .orElseThrow(() -> NotFoundException.of("Catalogue item", id));
        Map<String, Object> before = snapshot(it);
        apply(me, it, req);
        items.saveAndFlush(it);
        audit.record("CATALOGUE_ITEM", it.getId(), "UPDATE", before, snapshot(it));
        return view(it);
    }

    private void apply(CurrentUser me, CatalogueItem it, ItemIn req) {
        directory.serviceInCompany(req.serviceId(), me.companyId()).orElseThrow(() -> NotFoundException.of("Service", req.serviceId()));
        if (req.fulfilmentTeamId() != null) {
            directory.teamInCompany(req.fulfilmentTeamId(), me.companyId()).orElseThrow(() -> NotFoundException.of("Team", req.fulfilmentTeamId()));
        }
        List<StepIO> steps = req.steps() == null ? List.of() : req.steps();
        if (new HashSet<>(steps.stream().map(StepIO::stepOrder).toList()).size() != steps.size()) {
            throw new BusinessRuleException("Approval step orders must be unique.");
        }
        for (StepIO s : steps) {
            if ("ROLE".equals(s.approverType()) && (s.approverRole() == null || s.approverRole().isBlank())) {
                throw new BusinessRuleException("ROLE approval steps need approverRole.");
            }
            if ("ROLE".equals(s.approverType())) {
                try { Role.valueOf(s.approverRole()); } catch (IllegalArgumentException e) {
                    throw new BusinessRuleException("Unknown role " + s.approverRole() + ".");
                }
            }
        }
        it.apply(req.serviceId(), req.name().trim(), req.description(), req.baseCost() == null ? BigDecimal.ZERO : req.baseCost(),
                req.fulfilmentTeamId(), req.active() == null || req.active(),
                steps.stream().map(s -> new ApprovalStep(s.stepOrder(), s.approverType(),
                        "ROLE".equals(s.approverType()) ? s.approverRole() : null, s.minCost())).toList());
    }

    private Map<String, Object> snapshot(CatalogueItem it) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("serviceId", it.getServiceId());
        m.put("name", it.getName());
        m.put("baseCost", it.getBaseCost());
        m.put("fulfilmentTeamId", it.getFulfilmentTeamId());
        m.put("active", it.isActive());
        m.put("steps", it.getSteps().stream().sorted(java.util.Comparator.comparingInt(ApprovalStep::getStepOrder))
                .map(s -> s.getStepOrder() + ":" + s.getApproverType() + ":" + s.getApproverRole() + ">=" + s.getMinCost()).toList());
        return m;
    }
}
