package com.esmhub.request.service.catalogue;

import com.esmhub.request.service.catalogue.CatalogueDtos.*;
import com.esmhub.common.security.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/catalogue")
public class CatalogueController {
    private final CatalogueService service;

    public CatalogueController(CatalogueService service) { this.service = service; }

    @GetMapping
    public List<ItemView> list(CurrentUser me, @RequestParam(defaultValue = "false") boolean includeInactive) {
        return service.list(me, includeInactive);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ItemView create(CurrentUser me, @Valid @RequestBody ItemIn body) { return service.create(me, body); }

    @PutMapping("/{id}")
    public ItemView update(CurrentUser me, @PathVariable long id, @Valid @RequestBody ItemIn body) {
        return service.update(me, id, body);
    }
}
