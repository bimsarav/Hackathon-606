package com.esmhub.change.service.change;

import com.esmhub.change.service.change.ChangeDtos.*;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@Validated
@RequestMapping("/api/v1")
public class ChangeController {
    private final ChangeService service;

    public ChangeController(ChangeService service) { this.service = service; }

    @GetMapping("/changes")
    public PageResponse<ChangeView> list(CurrentUser me, @RequestParam(defaultValue = "all") String view,
                                         @RequestParam(required = false) String status,
                                         @RequestParam(required = false) String type,
                                         @RequestParam(required = false) String risk,
                                         @RequestParam(required = false) @Size(max = 100) String q,
                                         @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.list(me, view, status, type, risk, q, page, size);
    }

    @PostMapping("/changes")
    @ResponseStatus(HttpStatus.CREATED)
    public ChangeView create(CurrentUser me, @Valid @RequestBody ChangeIn body) { return service.create(me, body); }

    @GetMapping("/changes/{id}")
    public ChangeView get(CurrentUser me, @PathVariable long id) { return service.detail(me, id); }

    @PutMapping("/changes/{id}")
    public ChangeView update(CurrentUser me, @PathVariable long id, @Valid @RequestBody ChangeIn body) {
        return service.update(me, id, body);
    }

    @PostMapping("/changes/{id}/status")
    public ChangeView status(CurrentUser me, @PathVariable long id, @Valid @RequestBody StatusIn body) {
        return service.changeStatus(me, id, body.status());
    }

    @GetMapping("/changes-calendar")
    public List<CalendarEntry> calendar(CurrentUser me, @RequestParam(required = false) Instant from,
                                        @RequestParam(required = false) Instant to) {
        return service.calendar(me, from, to);
    }
}
