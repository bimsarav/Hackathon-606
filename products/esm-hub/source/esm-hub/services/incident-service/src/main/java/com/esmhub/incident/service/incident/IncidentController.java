package com.esmhub.incident.service.incident;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import com.esmhub.incident.service.incident.IncidentDtos.*;
import com.esmhub.incident.service.incident.IncidentService.Filter;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/** Incident lifecycle API (FR-3, FR-6, FR-14). */
@RestController
@Validated
@RequestMapping("/api/v1/incidents")
public class IncidentController {
    private final IncidentService service;

    public IncidentController(IncidentService service) { this.service = service; }

    public record PriorityView(int id, String name, int responseMinutes, int resolutionMinutes) {}

    @GetMapping
    public PageResponse<IncidentView> list(CurrentUser me, @RequestParam(required = false) @Size(max = 100) String q,
                                           @RequestParam(required = false) String status, @RequestParam(required = false) Integer priorityId,
                                           @RequestParam(required = false) Long teamId, @RequestParam(required = false) Long assigneeId,
                                           @RequestParam(required = false) Long requesterId, @RequestParam(defaultValue = "all") String view,
                                           @RequestParam(defaultValue = "false") boolean breached,
                                           @RequestParam(defaultValue = "created") String sort,
                                           @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.list(me, new Filter(q, status, priorityId, teamId, assigneeId, requesterId, view, breached, sort), page, size);
    }

    @GetMapping("/export")
    public ResponseEntity<byte[]> export(CurrentUser me, @RequestParam(required = false) @Size(max = 100) String q,
                                         @RequestParam(required = false) String status, @RequestParam(required = false) Integer priorityId,
                                         @RequestParam(required = false) Long teamId, @RequestParam(defaultValue = "all") String view,
                                         @RequestParam(defaultValue = "false") boolean breached) {
        return service.export(me, new Filter(q, status, priorityId, teamId, null, null, view, breached, "created"));
    }

    @GetMapping("/meta/priorities")
    public List<PriorityView> priorities() {
        return service.priorities().stream().map(p -> new PriorityView(p.getId(), p.getName(), p.getResponseMinutes(),
                p.getResolutionMinutes())).toList();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public IncidentView create(CurrentUser me, @Valid @RequestBody CreateIncident body,
                               @RequestHeader(value = "Idempotency-Key", required = false) String key) {
        return service.create(me, body, key);
    }

    @GetMapping("/{id}")
    public IncidentView get(CurrentUser me, @PathVariable long id) { return service.get(me, id); }

    @PatchMapping("/{id}")
    public IncidentView update(CurrentUser me, @PathVariable long id, @Valid @RequestBody UpdateIncident body) {
        return service.update(me, id, body);
    }

    @PostMapping("/{id}/assign")
    public IncidentView assign(CurrentUser me, @PathVariable long id, @Valid @RequestBody Assign body) {
        return service.assign(me, id, body);
    }

    @PostMapping("/{id}/status")
    public IncidentView status(CurrentUser me, @PathVariable long id, @Valid @RequestBody ChangeStatus body) {
        return service.changeStatus(me, id, body);
    }

    @PostMapping("/{id}/reopen")
    public IncidentView reopen(CurrentUser me, @PathVariable long id, @Valid @RequestBody Reopen body) {
        return service.reopen(me, id, body);
    }

    @PostMapping("/{id}/comments")
    @ResponseStatus(HttpStatus.CREATED)
    public CommentView comment(CurrentUser me, @PathVariable long id, @Valid @RequestBody AddComment body) {
        return service.comment(me, id, body);
    }

    @PostMapping("/{id}/worklogs")
    @ResponseStatus(HttpStatus.CREATED)
    public WorklogView worklog(CurrentUser me, @PathVariable long id, @Valid @RequestBody AddWorklog body) {
        return service.worklog(me, id, body);
    }

    @PostMapping("/{id}/satisfaction")
    public IncidentView rate(CurrentUser me, @PathVariable long id, @Valid @RequestBody Rate body) {
        return service.rate(me, id, body.score());
    }
}
