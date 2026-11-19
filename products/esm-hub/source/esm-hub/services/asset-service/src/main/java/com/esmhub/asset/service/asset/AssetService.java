package com.esmhub.asset.service.asset;

import com.esmhub.asset.service.asset.AssetDtos.*;
import com.esmhub.asset.service.events.AssetEvents;
import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.CsvWriter;
import com.esmhub.common.web.ConflictException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.DirUser;
import com.esmhub.directory.DirectoryLookup;
import jakarta.persistence.criteria.Predicate;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Inventory, lifecycle and assignment history (FR-9). */
@Service
public class AssetService {
    static final Role[] READERS = {Role.ASSET_MANAGER, Role.SERVICE_DESK_AGENT, Role.TECHNICIAN, Role.TEAM_LEAD,
            Role.SERVICE_MANAGER, Role.AUDITOR, Role.ADMIN};
    static final Role[] EXPORTERS = {Role.ASSET_MANAGER, Role.AUDITOR, Role.ADMIN, Role.SERVICE_MANAGER};
    static final int EXPORT_MAX_ROWS = 10_000;

    private final AssetRepository assets;
    private final AssetAssignmentRepository assignments;
    private final DirectoryLookup directory;
    private final AssetEvents events;
    private final AuditPublisher audit;

    public AssetService(AssetRepository assets, AssetAssignmentRepository assignments, DirectoryLookup directory,
                        AssetEvents events, AuditPublisher audit) {
        this.assets = assets;
        this.assignments = assignments;
        this.directory = directory;
        this.events = events;
        this.audit = audit;
    }

    // ---------- views ----------
    private AssetView view(Asset a, boolean detail) {
        List<HistoryEntry> history = detail ? assignments.findByAssetIdOrderByAssignedAtDescIdDesc(a.getId()).stream()
                .map(h -> new HistoryEntry(h.getUserId(), directory.name(h.getUserId()), h.getAssignedAt(), h.getReturnedAt(),
                        h.getAssignedBy())).toList() : null;
        return new AssetView(a.getId(), a.getAssetTag(), a.getAssetType(), a.getManufacturer(), a.getModel(), a.getSerialNumber(),
                a.getPurchaseDate(), a.getWarrantyEnd(), a.getOfficeId(), a.getPurchaseCost(), a.getStatus(), a.getAssignedUserId(),
                a.getAssignedUserId() == null ? null : directory.name(a.getAssignedUserId()),
                AssetRules.warrantyState(a.getWarrantyEnd(), LocalDate.now()), a.getCreatedAt(), history);
    }

    private static Map<String, Object> auditFields(Asset a) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("asset_tag", a.getAssetTag());
        m.put("asset_type", a.getAssetType());
        m.put("asset_status", a.getStatus());
        m.put("assigned_user_id", a.getAssignedUserId());
        m.put("office_id", a.getOfficeId());
        m.put("warranty_end", a.getWarrantyEnd() == null ? null : a.getWarrantyEnd().toString());
        m.put("purchase_cost", a.getPurchaseCost());
        return m;
    }

    private Asset scoped(CurrentUser me, long id) {
        Asset a = assets.findByIdAndCompanyId(id, me.companyId()).orElseThrow(() -> NotFoundException.of("Asset", id));
        if (!me.has(READERS) && !Long.valueOf(me.userId()).equals(a.getAssignedUserId())) {
            throw NotFoundException.of("Asset", id);
        }
        return a;
    }

    private Asset managed(CurrentUser me, long id) {
        me.require(Role.ASSET_MANAGER);
        return assets.findByIdAndCompanyId(id, me.companyId()).orElseThrow(() -> NotFoundException.of("Asset", id));
    }

    // ---------- queries ----------
    Specification<Asset> filter(CurrentUser me, String q, String status, String type, Long officeId, String warranty,
                                Long assigneeId) {
        LocalDate today = LocalDate.now();
        return (root, query, cb) -> {
            List<Predicate> p = new ArrayList<>();
            p.add(cb.equal(root.get("companyId"), me.companyId()));
            if (!me.has(READERS)) p.add(cb.equal(root.get("assignedUserId"), me.userId()));
            if (q != null && !q.isBlank()) {
                String like = "%" + q.trim().toLowerCase() + "%";
                p.add(cb.or(cb.like(cb.lower(root.get("assetTag")), like), cb.like(cb.lower(root.get("serialNumber")), like),
                        cb.like(cb.lower(root.get("model")), like)));
            }
            if (status != null && !status.isBlank()) p.add(root.get("status").in((Object[]) status.toUpperCase().split(",")));
            if (type != null && !type.isBlank()) p.add(cb.equal(root.get("assetType"), type));
            if (officeId != null) p.add(cb.equal(root.get("officeId"), officeId));
            if (assigneeId != null) p.add(cb.equal(root.get("assignedUserId"), assigneeId));
            if ("expired".equals(warranty)) p.add(cb.lessThan(root.<LocalDate>get("warrantyEnd"), today));
            if ("expiring".equals(warranty)) {
                p.add(cb.between(root.<LocalDate>get("warrantyEnd"), today, today.plusDays(AssetRules.EXPIRING_DAYS)));
            }
            return cb.and(p.toArray(Predicate[]::new));
        };
    }

    @Transactional(readOnly = true)
    public PageResponse<AssetView> list(CurrentUser me, String q, String status, String type, Long officeId, String warranty,
                                        Long assigneeId, int page, int size) {
        checkWarranty(warranty);
        var p = assets.findAll(filter(me, q, status, type, officeId, warranty, assigneeId),
                PageResponse.pageable(page, size, Sort.by("assetTag")));
        return PageResponse.of(p, a -> view(a, false));
    }

    private static void checkWarranty(String w) {
        if (w != null && !w.isBlank() && !w.equals("expired") && !w.equals("expiring")) {
            throw new BusinessRuleException("warranty must be 'expired' or 'expiring'.");
        }
    }

    @Transactional(readOnly = true)
    public AssetView get(CurrentUser me, long id) { return view(scoped(me, id), true); }

    @Transactional
    public ResponseEntity<byte[]> export(CurrentUser me, String status, String warranty) {
        me.require(EXPORTERS);
        checkWarranty(warranty);
        List<Asset> rows = assets.findAll(filter(me, null, status, null, null, warranty, null), Sort.by("assetTag"));
        if (rows.size() > EXPORT_MAX_ROWS) rows = rows.subList(0, EXPORT_MAX_ROWS);
        audit.record("ASSET", 0, "EXPORT", null, Map.of("rows", rows.size()));
        List<List<?>> out = rows.stream().<List<?>>map(a -> List.of(a.getAssetTag(), a.getAssetType(), nz(a.getManufacturer()),
                nz(a.getModel()), nz(a.getSerialNumber()), a.getStatus(),
                a.getAssignedUserId() == null ? "" : directory.name(a.getAssignedUserId()), nz(a.getOfficeId()),
                nz(a.getPurchaseDate()), nz(a.getWarrantyEnd()), nz(a.getPurchaseCost()))).collect(java.util.stream.Collectors.toList());
        return CsvWriter.response("assets.csv", List.of("asset_tag", "type", "manufacturer", "model", "serial", "status",
                "assigned_to", "office_id", "purchase_date", "warranty_end", "purchase_cost"), out);
    }

    private static Object nz(Object o) { return o == null ? "" : o; }

    // ---------- commands ----------
    private void checkOffice(CurrentUser me, Long officeId) {
        if (officeId != null && directory.office(officeId).filter(o -> o.getCompanyId() == me.companyId()).isEmpty()) {
            throw NotFoundException.of("Office", officeId);
        }
    }

    private static void checkDates(Asset a) {
        if (a.getWarrantyEnd() != null && a.getPurchaseDate() != null && a.getWarrantyEnd().isBefore(a.getPurchaseDate())) {
            throw new BusinessRuleException("warrantyEnd cannot be before purchaseDate.");
        }
    }

    @Transactional
    public AssetView create(CurrentUser me, CreateAsset in) {
        me.require(Role.ASSET_MANAGER);
        checkOffice(me, in.officeId());
        if (assets.existsByCompanyIdAndAssetTagIgnoreCase(me.companyId(), in.assetTag().trim())) {
            throw new ConflictException("Asset tag " + in.assetTag() + " already exists.");
        }
        if (in.serialNumber() != null && assets.existsByCompanyIdAndSerialNumber(me.companyId(), in.serialNumber())) {
            throw new ConflictException("Serial number " + in.serialNumber() + " already exists.");
        }
        Asset a = new Asset(me.companyId(), in.assetTag().trim(), in.assetType().trim());
        a.setDetails(in.manufacturer(), in.model(), in.serialNumber(), in.purchaseDate(), in.warrantyEnd(), in.officeId(), in.purchaseCost());
        checkDates(a);
        assets.saveAndFlush(a);
        audit.record("ASSET", a.getId(), "CREATE", null, auditFields(a));
        events.snapshot(a);
        return view(a, true);
    }

    @Transactional
    public AssetView update(CurrentUser me, long id, UpdateAsset in) {
        Asset a = managed(me, id);
        Map<String, Object> before = auditFields(a);
        if (in.officeId() != null) { checkOffice(me, in.officeId()); a.setOfficeId(in.officeId()); }
        if (in.manufacturer() != null) a.setManufacturer(in.manufacturer());
        if (in.model() != null) a.setModel(in.model());
        if (in.warrantyEnd() != null) a.setWarrantyEnd(in.warrantyEnd());
        if (in.purchaseCost() != null) a.setPurchaseCost(in.purchaseCost());
        checkDates(a);
        a.touch();
        assets.saveAndFlush(a);
        audit.record("ASSET", a.getId(), "UPDATE", before, auditFields(a));
        events.snapshot(a);
        return view(a, true);
    }

    @Transactional
    public AssetView assign(CurrentUser me, long id, long userId) {
        Asset a = managed(me, id);
        DirUser u = directory.userInCompany(userId, me.companyId()).orElseThrow(() -> NotFoundException.of("User", userId));
        if (!AssetRules.canAssignFrom(a.getStatus())) {
            throw new BusinessRuleException("An asset in " + a.getStatus() + " cannot be assigned.");
        }
        if (!u.isActive()) throw new BusinessRuleException("Cannot assign to an inactive user.");
        Map<String, Object> before = auditFields(a);
        Instant now = Instant.now();
        closeOpenAssignment(a, now);
        assignments.saveAndFlush(new AssetAssignment(a.getId(), u.getUserId(), now, me.userId()));
        a.setAssignedUserId(u.getUserId());
        a.setStatus(AssetRules.ASSIGNED);
        a.touch();
        assets.saveAndFlush(a);
        audit.record("ASSET", a.getId(), "ASSIGN", before, auditFields(a));
        events.assigned(a, u.getUserId());
        events.snapshot(a);
        return view(a, true);
    }

    @Transactional
    public AssetView changeStatus(CurrentUser me, long id, String to) {
        Asset a = managed(me, id);
        if (AssetRules.ASSIGNED.equals(to)) throw new BusinessRuleException("Use the assign operation to assign an asset.");
        if (!AssetRules.canMove(a.getStatus(), to)) {
            throw new BusinessRuleException("Transition " + a.getStatus() + " -> " + to + " is not allowed.");
        }
        Map<String, Object> before = auditFields(a);
        if (a.getAssignedUserId() != null) {
            closeOpenAssignment(a, Instant.now());
            a.setAssignedUserId(null);
        }
        a.setStatus(to);
        a.touch();
        assets.saveAndFlush(a);
        audit.record("ASSET", a.getId(), "STATUS_CHANGE", before, auditFields(a));
        events.snapshot(a);
        return view(a, true);
    }

    private void closeOpenAssignment(Asset a, Instant now) {
        assignments.findByAssetIdAndReturnedAtIsNull(a.getId()).ifPresent(h -> {
            h.close(now);
            assignments.saveAndFlush(h);
        });
    }
}
