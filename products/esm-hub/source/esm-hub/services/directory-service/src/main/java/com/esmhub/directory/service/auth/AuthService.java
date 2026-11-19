package com.esmhub.directory.service.auth;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.directory.service.org.TeamRepository;
import com.esmhub.directory.service.user.User;
import com.esmhub.directory.service.user.UserRepository;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Login with lockout (FR-1): 5 failures lock the account for 15 minutes. Unknown users, wrong passwords, locked and
 * inactive accounts all get the same answer, and an unknown email still costs one bcrypt check (no user enumeration).
 */
@Service
public class AuthService {

    private final UserRepository users;
    private final TeamRepository teams;
    private final PasswordEncoder encoder;
    private final TokenService tokens;
    private final AuditPublisher audit;
    private final Clock clock;
    private final int maxFailures;
    private final Duration lockFor;
    /** bcrypt hash of a random value, checked for unknown users so timing does not reveal them. */
    private final String dummyHash;

    public AuthService(UserRepository users, TeamRepository teams, PasswordEncoder encoder, TokenService tokens,
                       AuditPublisher audit, Clock clock, @Value("${esm.auth.max-failed-logins:5}") int maxFailures,
                       @Value("${esm.auth.lock-minutes:15}") int lockMinutes) {
        this.users = users;
        this.teams = teams;
        this.encoder = encoder;
        this.tokens = tokens;
        this.audit = audit;
        this.clock = clock;
        this.maxFailures = maxFailures;
        this.lockFor = Duration.ofMinutes(lockMinutes);
        this.dummyHash = encoder.encode(java.util.UUID.randomUUID().toString());
    }

    /** Returns a token, or empty for any kind of rejection (the caller answers 401 uniformly). */
    @Transactional(noRollbackFor = RuntimeException.class)
    public Optional<TokenService.Token> login(String email, String password) {
        Instant now = clock.instant();
        Optional<User> found = users.findByEmailIgnoreCase(email.trim());
        if (found.isEmpty()) {
            encoder.matches(password, dummyHash);
            return Optional.empty();
        }
        User u = found.get();
        boolean locked = u.isLocked(now);
        boolean ok = u.getPasswordHash() != null && encoder.matches(password, u.getPasswordHash());
        if (!ok || locked || "INACTIVE".equals(u.getEmploymentStatus())) {
            if (!locked) {
                u.loginFailed(maxFailures, now.plus(lockFor));
                audit.record("USER", u.getId(), "LOGIN_FAILED", null, Map.of("locked", u.isLocked(now)));
            }
            return Optional.empty();
        }
        u.loginSucceeded(now);
        audit.record("USER", u.getId(), "LOGIN", null, null);
        return Optional.of(tokens.issue(u, teams.findTeamIdsOfUser(u.getId())));
    }

    @Transactional
    public void changePassword(long userId, String current, String next) {
        User u = users.findById(userId).orElseThrow();
        if (u.getPasswordHash() == null || !encoder.matches(current, u.getPasswordHash())) {
            throw new BusinessRuleException("Current password is incorrect.");
        }
        PasswordPolicy.check(next);
        u.setPassword(encoder.encode(next));
        audit.record("USER", userId, "PASSWORD_CHANGE", null, null);
    }
}
