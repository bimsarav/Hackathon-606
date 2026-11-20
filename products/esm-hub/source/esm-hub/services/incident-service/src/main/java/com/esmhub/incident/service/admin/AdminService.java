package com.esmhub.incident.service.admin;

import static com.esmhub.common.security.Role.*;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.NotFoundException;
import com.esmhub.directory.DirectoryLookup;
import com.esmhub.incident.service.admin.AdminDtos.*;
import com.esmhub.incident.service.reference.AssignmentRule;
import com.esmhub.incident.service.reference.AssignmentRuleRepository;
import com.esmhub.incident.service.reference.BusinessCalendar;
import com.esmhub.incident.service.reference.BusinessCalendarRepository;
import com.esmhub.incident.service.reference.EscalationRule;
import com.esmhub.incident.service.reference.EscalationRuleRepository;
import com.esmhub.incident.service.reference.Priority;
import com.esmhub.incident.service.reference.PriorityRepository;
import com.esmhub.incident.service.reference.SlaPolicy;
import com.esmhub.incident.service.reference.SlaPolicyRepository;
import com.esmhub.incident.service.reference.TimezoneCalendar;
import com.esmhub.incident.service.reference.TimezoneCalendarRepository;
import java.time.DateTimeException;
import java.time.ZoneId;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Configuration the service manager owns: priorities, versioned SLA policies, calendars, routing and escalation rules. */
@Service
public class AdminService {
    static final Role[] CONFIG = {SERVICE_MANAGER, ADMIN};
    static final Role[] SLA_READERS = {SERVICE_MANAGER, ADMIN, AUDITOR, TEAM_LEAD};
    static final Role[] RULE_READERS = {SERVICE_MANAGER, ADMIN, TEAM_LEAD, SERVICE_DESK_AGENT};
    static final Role[] ESC_READERS = {SERVICE_MANAGER, ADMIN, TEAM_LEAD};

    private final PriorityRepository priorities;
    private final SlaPolicyRepository policies;
    private final BusinessCalendarRepository calendars;
    private final TimezoneCalendarRepository tzCalendars;
    private final AssignmentRuleRepository rules;
    private final EscalationRuleRepository escalations;
    private final DirectoryLookup directory;
    private final AuditPublisher audit;

    public AdminService(PriorityRepository priorities, SlaPolicyRepository policies, BusinessCalendarRepository calendars,
                        TimezoneCalendarRepository tzCalendars, AssignmentRuleRepository rules,
                        EscalationRuleRepository escalations, DirectoryLookup directory, AuditPublisher audit) {
        this.priorities = priorities;
        this.policies = policies;
        this.calendars = calendars;
        this.tzCalendars = tzCalendars;
        this.rules = rules;
        this.escalations = escalations;
        this.directory = directory;
        this.audit = audit;
    }

    // ---------- priorities ----------
    @Transactional
    public PriorityView updatePriority(CurrentUser me, int id, PriorityIn b) {
        me.require(CONFIG);
        Priority p = priorities.findById(id).orElseThrow(() -> new NotFoundException("Priority not found."));
        if (b.resolutionMinutes() < b.responseMinutes()) throw new BusinessRuleException("Resolution target must be ≥ response target.");
        var before = Map.<String, Object>of("responseMinutes", p.getResponseMinutes(), "resolutionMinutes", p.getResolutionMinutes());
        p.setTargets(b.responseMinutes(), b.resolutionMinutes());
        audit.record("PRIORITY", id, "UPDATE", before,
                Map.of("responseMinutes", b.responseMinutes(), "resolutionMinutes", b.resolutionMinutes()));
        return new PriorityView(id, p.getName(), p.getResponseMinutes(), p.getResolutionMinutes());
    }

    // ---------- SLA policies ----------
    static SlaView view(SlaPolicy p) {
        return new SlaView(p.getId(), p.getCompanyId(), p.getName(), p.getPriorityId(), p.getServiceId(), p.isBusinessHoursOnly(),
                p.getResponseTargetMinutes(), p.getResolutionTargetMinutes(), p.getEffectiveFrom(), p.getEffectiveTo(), p.getVersion());
    }

    @Transactional(readOnly = true)
    public List<SlaView> listSla(CurrentUser me) {
        me.require(SLA_READERS);
        return policies.visible(me.companyId()).stream().map(AdminService::view).toList();
    }

    /** New policy version: the current version for the same priority and service ends the day before (history kept). */
    @Transactional
    public SlaView newSlaVersion(CurrentUser me, SlaIn b) {
        me.require(CONFIG);
        if (b.resolutionTargetMinutes() < b.responseTargetMinutes()) throw new BusinessRuleException("Resolution target must be ≥ response target.");
        if (b.serviceId() != null && directory.serviceInCompany(b.serviceId(), me.companyId()).isEmpty()) {
            throw new NotFoundException("Service not found.");
        }
        List<SlaPolicy> current = b.serviceId() == null ? policies.currentGeneral(me.companyId(), b.priorityId())
                : policies.currentForService(me.companyId(), b.priorityId(), b.serviceId());
        int version = 1;
        for (SlaPolicy p : current) {
            if (!p.getEffectiveFrom().isBefore(b.effectiveFrom())) {
                throw new BusinessRuleException("effective_from must be after the current version's start.");
            }
            p.endOn(b.effectiveFrom().minusDays(1));
            version = Math.max(version, p.getVersion() + 1);
        }
        SlaPolicy pol = policies.saveAndFlush(new SlaPolicy(me.companyId(), b.name(), b.priorityId(), b.serviceId(),
                b.businessHoursOnly() == null || b.businessHoursOnly(), b.responseTargetMinutes(), b.resolutionTargetMinutes(), b.effectiveFrom(), version));
        audit.record("SLA_POLICY", pol.getId(), "CREATE", null, Map.of("name", b.name(), "priorityId", b.priorityId(),
                "version", version, "effectiveFrom", b.effectiveFrom().toString()));
        return view(pol);
    }

    // ---------- calendars ----------
    static CalendarView view(BusinessCalendar c) {
        return new CalendarView(c.getId(), c.getName(), c.getTimezone(),
                c.getHours().stream().sorted(Comparator.comparingInt(BusinessCalendar.Hours::weekday))
                        .map(h -> new HoursIn(h.weekday(), h.startTime(), h.endTime())).toList(),
                c.getHolidays().stream().sorted(Comparator.comparing(BusinessCalendar.Holiday::holidayDate))
                        .map(h -> new HolidayIn(h.holidayDate(), h.name())).toList());
    }

    @Transactional(readOnly = true)
    public List<CalendarView> listCalendars() { return calendars.findAllByOrderByName().stream().map(AdminService::view).toList(); }

    private void validate(CalendarIn b) {
        try {
            ZoneId.of(b.timezone());
        } catch (DateTimeException e) {
            throw new BusinessRuleException("Unknown IANA timezone.");
        }
        Set<Integer> days = new HashSet<>();
        for (HoursIn h : b.hours()) {
            if (!days.add(h.weekday())) throw new BusinessRuleException("Duplicate weekday.");
            if (!h.endTime().isAfter(h.startTime())) throw new BusinessRuleException("end_time must be after start_time.");
        }
    }

    private void apply(BusinessCalendar c, CalendarIn b) {
        c.update(b.name(), b.timezone(),
                b.hours().stream().map(h -> new BusinessCalendar.Hours(h.weekday(), h.startTime(), h.endTime())).toList(),
                (b.holidays() == null ? List.<HolidayIn>of() : b.holidays()).stream()
                        .map(h -> new BusinessCalendar.Holiday(h.holidayDate(), h.name())).toList());
    }

    /** Offices in a timezone use the calendar mapped to it; a new timezone maps to the calendar that introduced it. */
    private void mapTimezone(BusinessCalendar c) {
        if (!tzCalendars.existsById(c.getTimezone())) tzCalendars.save(new TimezoneCalendar(c.getTimezone(), c.getId()));
    }

    @Transactional
    public CalendarView createCalendar(CurrentUser me, CalendarIn b) {
        me.require(CONFIG);
        validate(b);
        BusinessCalendar c = new BusinessCalendar(b.name(), b.timezone());
        apply(c, b);
        c = calendars.saveAndFlush(c);
        mapTimezone(c);
        audit.record("CALENDAR", c.getId(), "CREATE", null, Map.of("name", b.name()));
        return view(c);
    }

    @Transactional
    public CalendarView updateCalendar(CurrentUser me, long id, CalendarIn b) {
        me.require(CONFIG);
        validate(b);
        BusinessCalendar c = calendars.findById(id).orElseThrow(() -> new NotFoundException("Calendar not found."));
        var before = Map.<String, Object>of("hours", c.getHours().size(), "holidays", c.getHolidays().size());
        apply(c, b);
        calendars.flush();
        mapTimezone(c);
        audit.record("CALENDAR", id, "UPDATE", before,
                Map.of("hours", b.hours().size(), "holidays", b.holidays() == null ? 0 : b.holidays().size()));
        return view(c);
    }

    // ---------- assignment rules ----------
    static RuleView view(AssignmentRule r) {
        return new RuleView(r.getId(), r.getServiceId(), r.getPriorityId(), r.getTeamId(), r.getSortOrder(), r.isActive());
    }

    @Transactional(readOnly = true)
    public List<RuleView> listRules(CurrentUser me) {
        me.require(RULE_READERS);
        return rules.findByCompanyIdOrderBySortOrderAscIdAsc(me.companyId()).stream().map(AdminService::view).toList();
    }

    @Transactional
    public RuleView saveRule(CurrentUser me, Long id, RuleIn b) {
        me.require(CONFIG);
        if (directory.teamInCompany(b.teamId(), me.companyId()).isEmpty()) throw new NotFoundException("Team not found.");
        if (b.serviceId() != null && directory.serviceInCompany(b.serviceId(), me.companyId()).isEmpty()) {
            throw new NotFoundException("Service not found.");
        }
        AssignmentRule r = id == null ? new AssignmentRule(me.companyId())
                : rules.findById(id).filter(x -> x.getCompanyId() == me.companyId())
                        .orElseThrow(() -> new NotFoundException("Assignment rule not found."));
        r.update(b.serviceId(), b.priorityId(), b.teamId(), b.sortOrder() == null ? 100 : b.sortOrder(),
                b.active() == null || b.active());
        r = rules.saveAndFlush(r);
        audit.record("ASSIGNMENT_RULE", r.getId(), id == null ? "CREATE" : "UPDATE", null,
                Map.of("teamId", r.getTeamId(), "sortOrder", r.getSortOrder(), "active", r.isActive()));
        return view(r);
    }

    // ---------- escalation rules ----------
    static EscalationView view(EscalationRule r) {
        return new EscalationView(r.getId(), r.getPriorityId(), r.getTrigger(), r.getNotifyRole(), r.isNotifyAssignee(), r.isActive());
    }

    @Transactional(readOnly = true)
    public List<EscalationView> listEscalations(CurrentUser me) {
        me.require(ESC_READERS);
        return escalations.visible(me.companyId()).stream().map(AdminService::view).toList();
    }

    @Transactional
    public EscalationView createEscalation(CurrentUser me, EscalationIn b) {
        me.require(CONFIG);
        boolean known = "TEAM_LEAD".equals(b.notifyRole()) || Arrays.stream(Role.values()).anyMatch(r -> r.name().equals(b.notifyRole()));
        if (!known) throw new BusinessRuleException("Unknown role.");
        EscalationRule r = new EscalationRule(me.companyId());
        r.update(b.priorityId(), b.trigger(), b.notifyRole(), b.notifyAssignee() == null || b.notifyAssignee(),
                b.active() == null || b.active());
        r = escalations.saveAndFlush(r);
        audit.record("ESCALATION_RULE", r.getId(), "CREATE", null, Map.of("trigger", b.trigger(), "notifyRole", b.notifyRole()));
        return view(r);
    }
}
