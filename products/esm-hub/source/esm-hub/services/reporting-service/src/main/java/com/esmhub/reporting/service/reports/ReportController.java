package com.esmhub.reporting.service.reports;

import com.esmhub.common.security.CurrentUser;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/reports")
public class ReportController {
    private final ReportService service;

    public ReportController(ReportService service) { this.service = service; }

    private static final String ISO = "yyyy-MM-dd";

    @GetMapping("/summary")
    public Map<String, Object> summary(CurrentUser me, @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate since,
                                       @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate until) {
        return service.summary(me, since, until);
    }

    @GetMapping("/incident-volume")
    public List<Map<String, Object>> incidentVolume(CurrentUser me, @RequestParam(defaultValue = "month") String by,
                                                    @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate since,
                                                    @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate until) {
        return service.incidentVolume(me, by, since, until);
    }

    @GetMapping("/sla-compliance")
    public List<Map<String, Object>> sla(CurrentUser me, @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate since,
                                         @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate until) {
        return service.slaCompliance(me, since, until);
    }

    @GetMapping("/backlog-ageing")
    public List<Map<String, Object>> backlog(CurrentUser me) { return service.backlogAgeing(me); }

    @GetMapping("/workload")
    public List<Map<String, Object>> workload(CurrentUser me, @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate since,
                                              @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate until) {
        return service.workload(me);
    }

    @GetMapping("/assets")
    public List<Map<String, Object>> assets(CurrentUser me) { return service.assets(me); }

    @GetMapping("/requests")
    public List<Map<String, Object>> requests(CurrentUser me, @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate since,
                                              @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate until) {
        return service.requests(me, since, until);
    }

    @GetMapping("/changes")
    public List<Map<String, Object>> changes(CurrentUser me) { return service.changes(me); }

    @GetMapping("/problems")
    public Map<String, Object> problems(CurrentUser me) { return service.problems(me); }

    @GetMapping("/{name}/export")
    public ResponseEntity<byte[]> export(CurrentUser me, @PathVariable String name, @RequestParam(defaultValue = "month") String by,
                                         @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate since,
                                         @RequestParam(required = false) @DateTimeFormat(pattern = ISO) LocalDate until) {
        return service.export(me, name, by, since, until);
    }
}
