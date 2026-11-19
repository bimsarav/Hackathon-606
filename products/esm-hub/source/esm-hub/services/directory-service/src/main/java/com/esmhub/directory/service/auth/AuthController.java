package com.esmhub.directory.service.auth;

import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.web.GlobalExceptionHandler;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {
    private final AuthService auth;

    public AuthController(AuthService auth) { this.auth = auth; }

    public record LoginRequest(@NotBlank @Size(max = 160) String email, @NotBlank @Size(max = 200) String password) {}
    public record TokenResponse(String accessToken, String tokenType, long expiresIn) {}
    public record MeResponse(long userId, long companyId, String name, String email, List<String> roles, List<Long> teamIds) {}
    public record PasswordChange(@NotBlank String currentPassword, @NotBlank @Size(max = 200) String newPassword) {}

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest req) {
        return auth.login(req.email(), req.password())
                .<ResponseEntity<?>>map(t -> ResponseEntity.ok(new TokenResponse(t.accessToken(), "Bearer", t.expiresIn())))
                .orElseGet(() -> {
                    ProblemDetail pd = GlobalExceptionHandler.problem(HttpStatus.UNAUTHORIZED, "Unauthorized",
                            "Invalid credentials or account locked.");
                    return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(pd);
                });
    }

    @GetMapping("/me")
    public MeResponse me(CurrentUser user) {
        return new MeResponse(user.userId(), user.companyId(), user.name(), user.email(),
                user.roles().stream().sorted().toList(), user.teamIds().stream().sorted().toList());
    }

    @PostMapping("/password")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void changePassword(CurrentUser user, @Valid @RequestBody PasswordChange body) {
        auth.changePassword(user.userId(), body.currentPassword(), body.newPassword());
    }
}
