package com.esmhub.request.service.request;

import com.esmhub.request.service.request.RequestDtos.*;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@Validated
@RequestMapping("/api/v1/requests")
public class RequestController {
    private final RequestService service;

    public RequestController(RequestService service) { this.service = service; }

    @GetMapping
    public PageResponse<RequestView> list(CurrentUser me, @RequestParam(defaultValue = "all") String view,
                                          @RequestParam(required = false) String status,
                                          @RequestParam(required = false) @Size(max = 100) String q,
                                          @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.list(me, view, status, q, page, size);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public RequestView create(CurrentUser me, @Valid @RequestBody CreateRequest body,
                              @RequestHeader(value = "Idempotency-Key", required = false) @Size(max = 100) String key) {
        return service.create(me, body, key);
    }

    @GetMapping("/{id}")
    public RequestView get(CurrentUser me, @PathVariable long id) { return service.detail(me, id); }

    @PostMapping("/{id}/status")
    public RequestView status(CurrentUser me, @PathVariable long id, @Valid @RequestBody StatusIn body) {
        return service.changeStatus(me, id, body.status());
    }
}
