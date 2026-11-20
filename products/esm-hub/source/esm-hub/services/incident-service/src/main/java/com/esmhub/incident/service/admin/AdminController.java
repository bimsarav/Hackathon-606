package com.esmhub.incident.service.admin;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.incident.service.admin.AdminDtos.*;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/admin")
public class AdminController {
    private final AdminService service;

    public AdminController(AdminService service) { this.service = service; }

    @PutMapping("/priorities/{id}")
    public PriorityView priority(CurrentUser me, @PathVariable int id, @Valid @RequestBody PriorityIn body) {
        return service.updatePriority(me, id, body);
    }

    @GetMapping("/sla-policies")
    public List<SlaView> slaPolicies(CurrentUser me) { return service.listSla(me); }

    @PostMapping("/sla-policies")
    @ResponseStatus(HttpStatus.CREATED)
    public SlaView newSla(CurrentUser me, @Valid @RequestBody SlaIn body) { return service.newSlaVersion(me, body); }

    @GetMapping("/calendars")
    public List<CalendarView> calendars() { return service.listCalendars(); }

    @PostMapping("/calendars")
    @ResponseStatus(HttpStatus.CREATED)
    public CalendarView createCalendar(CurrentUser me, @Valid @RequestBody CalendarIn body) { return service.createCalendar(me, body); }

    @PutMapping("/calendars/{id}")
    public CalendarView updateCalendar(CurrentUser me, @PathVariable long id, @Valid @RequestBody CalendarIn body) {
        return service.updateCalendar(me, id, body);
    }

    @GetMapping("/assignment-rules")
    public List<RuleView> rules(CurrentUser me) { return service.listRules(me); }

    @PostMapping("/assignment-rules")
    @ResponseStatus(HttpStatus.CREATED)
    public RuleView createRule(CurrentUser me, @Valid @RequestBody RuleIn body) { return service.saveRule(me, null, body); }

    @PutMapping("/assignment-rules/{id}")
    public RuleView updateRule(CurrentUser me, @PathVariable long id, @Valid @RequestBody RuleIn body) {
        return service.saveRule(me, id, body);
    }

    @GetMapping("/escalation-rules")
    public List<EscalationView> escalations(CurrentUser me) { return service.listEscalations(me); }

    @PostMapping("/escalation-rules")
    @ResponseStatus(HttpStatus.CREATED)
    public EscalationView createEscalation(CurrentUser me, @Valid @RequestBody EscalationIn body) {
        return service.createEscalation(me, body);
    }
}
