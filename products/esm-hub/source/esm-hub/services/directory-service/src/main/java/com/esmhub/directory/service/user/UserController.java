package com.esmhub.directory.service.user;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.PageResponse;
import com.esmhub.directory.service.user.UserDtos.CreateUser;
import com.esmhub.directory.service.user.UserDtos.SetPassword;
import com.esmhub.directory.service.user.UserDtos.UpdateUser;
import com.esmhub.directory.service.user.UserDtos.UserView;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@Validated
@RequestMapping("/api/v1")
public class UserController {
    private final UserService service;

    public UserController(UserService service) { this.service = service; }

    @GetMapping("/users")
    public PageResponse<UserView> search(CurrentUser me, @RequestParam(required = false) @Size(max = 100) String q,
                                         @RequestParam(defaultValue = "false") boolean includeInactive,
                                         @RequestParam(defaultValue = "1") int page, @RequestParam(defaultValue = "25") int size) {
        return service.search(me, q, includeInactive, page, size);
    }

    @GetMapping("/users/{id}")
    public UserView get(CurrentUser me, @PathVariable long id) { return service.get(me, id); }

    @PostMapping("/admin/users")
    @ResponseStatus(HttpStatus.CREATED)
    public UserView create(CurrentUser me, @Valid @RequestBody CreateUser body) { return service.create(me, body); }

    @PatchMapping("/admin/users/{id}")
    public UserView update(CurrentUser me, @PathVariable long id, @Valid @RequestBody UpdateUser body) {
        return service.update(me, id, body);
    }

    @PostMapping("/admin/users/{id}/password")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void resetPassword(CurrentUser me, @PathVariable long id, @Valid @RequestBody SetPassword body) {
        service.resetPassword(me, id, body.newPassword());
    }
}
