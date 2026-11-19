package com.esmhub.asset.service.asset;

import com.esmhub.asset.service.asset.AssetDtos.*;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@Validated
@RequestMapping("/api/v1/assets")
public class AssetController {
    private final AssetService service;

    public AssetController(AssetService service) { this.service = service; }

    @GetMapping
    public PageResponse<AssetView> list(CurrentUser me, @RequestParam(required = false) @Size(max = 100) String q,
                                        @RequestParam(required = false) String status, @RequestParam(required = false) String type,
                                        @RequestParam(required = false) Long officeId, @RequestParam(required = false) String warranty,
                                        @RequestParam(required = false) Long assigneeId,
                                        @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.list(me, q, status, type, officeId, warranty, assigneeId, page, size);
    }

    @GetMapping("/export")
    public ResponseEntity<byte[]> export(CurrentUser me, @RequestParam(required = false) String status,
                                         @RequestParam(required = false) String warranty) {
        return service.export(me, status, warranty);
    }

    @GetMapping("/{id}")
    public AssetView get(CurrentUser me, @PathVariable long id) { return service.get(me, id); }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public AssetView create(CurrentUser me, @Valid @RequestBody CreateAsset body) { return service.create(me, body); }

    @PatchMapping("/{id}")
    public AssetView update(CurrentUser me, @PathVariable long id, @Valid @RequestBody UpdateAsset body) {
        return service.update(me, id, body);
    }

    @PostMapping("/{id}/assign")
    public AssetView assign(CurrentUser me, @PathVariable long id, @Valid @RequestBody AssignAsset body) {
        return service.assign(me, id, body.userId());
    }

    @PostMapping("/{id}/status")
    public AssetView status(CurrentUser me, @PathVariable long id, @Valid @RequestBody ChangeStatus body) {
        return service.changeStatus(me, id, body.status());
    }
}
