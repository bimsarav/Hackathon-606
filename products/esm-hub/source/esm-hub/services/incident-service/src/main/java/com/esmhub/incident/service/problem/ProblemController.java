package com.esmhub.incident.service.problem;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import com.esmhub.incident.service.problem.ProblemDtos.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@Validated
@RequestMapping("/api/v1/problems")
public class ProblemController {
    private final ProblemService service;

    public ProblemController(ProblemService service) { this.service = service; }

    @GetMapping
    public PageResponse<ProblemView> list(CurrentUser me, @RequestParam(required = false) String status,
                                          @RequestParam(required = false) Boolean knownError,
                                          @RequestParam(required = false) @Size(max = 100) String q,
                                          @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.list(me, status, knownError, q, page, size);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProblemView create(CurrentUser me, @Valid @RequestBody CreateProblem body) { return service.create(me, body); }

    @GetMapping("/{id}")
    public ProblemView get(CurrentUser me, @PathVariable long id) { return service.get(me, id); }

    @PatchMapping("/{id}")
    public ProblemView update(CurrentUser me, @PathVariable long id, @Valid @RequestBody UpdateProblem body) {
        return service.update(me, id, body);
    }

    @PostMapping("/{id}/incidents")
    public ProblemView link(CurrentUser me, @PathVariable long id, @Valid @RequestBody LinkIncidents body) {
        return service.linkIncidents(me, id, body.incidentIds());
    }

    @DeleteMapping("/{id}/incidents/{incidentId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void unlink(CurrentUser me, @PathVariable long id, @PathVariable long incidentId) {
        service.unlink(me, id, incidentId);
    }
}
