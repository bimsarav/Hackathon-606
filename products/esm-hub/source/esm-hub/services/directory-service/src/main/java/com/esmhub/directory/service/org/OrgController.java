package com.esmhub.directory.service.org;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.directory.service.org.OrgDtos.*;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class OrgController {
    private final OrgService service;

    public OrgController(OrgService service) { this.service = service; }

    /** Everything the UI needs for pick lists, in one call. */
    @GetMapping("/reference")
    public Reference reference(CurrentUser me) { return service.reference(me); }

    @GetMapping("/teams/{id}/members")
    public List<MemberView> members(CurrentUser me, @PathVariable long id) { return service.members(me, id); }

    @PostMapping("/admin/offices") @ResponseStatus(HttpStatus.CREATED)
    public OfficeView createOffice(CurrentUser me, @Valid @RequestBody OfficeInput in) { return service.saveOffice(me, null, in); }

    @PutMapping("/admin/offices/{id}")
    public OfficeView updateOffice(CurrentUser me, @PathVariable long id, @Valid @RequestBody OfficeInput in) { return service.saveOffice(me, id, in); }

    @PostMapping("/admin/departments") @ResponseStatus(HttpStatus.CREATED)
    public DepartmentView createDepartment(CurrentUser me, @Valid @RequestBody DepartmentInput in) { return service.createDepartment(me, in); }

    @PostMapping("/admin/teams") @ResponseStatus(HttpStatus.CREATED)
    public TeamView createTeam(CurrentUser me, @Valid @RequestBody TeamInput in) { return service.saveTeam(me, null, in); }

    @PutMapping("/admin/teams/{id}")
    public TeamView updateTeam(CurrentUser me, @PathVariable long id, @Valid @RequestBody TeamInput in) { return service.saveTeam(me, id, in); }

    @PostMapping("/admin/categories") @ResponseStatus(HttpStatus.CREATED)
    public CategoryView createCategory(CurrentUser me, @Valid @RequestBody CategoryInput in) { return service.createCategory(me, in); }

    @PostMapping("/admin/services") @ResponseStatus(HttpStatus.CREATED)
    public ServiceView createService(CurrentUser me, @Valid @RequestBody ServiceInput in) { return service.saveService(me, null, in); }

    @PutMapping("/admin/services/{id}")
    public ServiceView updateService(CurrentUser me, @PathVariable long id, @Valid @RequestBody ServiceInput in) { return service.saveService(me, id, in); }
}
