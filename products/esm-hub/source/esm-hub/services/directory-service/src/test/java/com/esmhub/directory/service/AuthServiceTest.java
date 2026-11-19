package com.esmhub.directory.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.directory.service.auth.AuthService;
import com.esmhub.directory.service.auth.PasswordPolicy;
import com.esmhub.directory.service.auth.TokenService;
import com.esmhub.directory.service.org.TeamRepository;
import com.esmhub.directory.service.user.User;
import com.esmhub.directory.service.user.UserRepository;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.password.PasswordEncoder;

class AuthServiceTest {
    UserRepository users = mock(UserRepository.class);
    TeamRepository teams = mock(TeamRepository.class);
    PasswordEncoder encoder = mock(PasswordEncoder.class);
    TokenService tokens = mock(TokenService.class);
    AuditPublisher audit = mock(AuditPublisher.class);
    Clock clock = Clock.fixed(Instant.parse("2026-11-19T10:00:00Z"), ZoneOffset.UTC);
    AuthService service;
    User user;

    @BeforeEach
    void setUp() {
        when(encoder.encode(anyString())).thenReturn("dummy");
        service = new AuthService(users, teams, encoder, tokens, audit, clock, 3, 15);
        user = new User(1, "E1", "a@example.test");
        user.setPassword("hash");
        org.springframework.test.util.ReflectionTestUtils.setField(user, "id", 1L);
        when(users.findByEmailIgnoreCase("a@example.test")).thenReturn(Optional.of(user));
        when(teams.findTeamIdsOfUser(anyLong())).thenReturn(List.of());
    }

    @Test
    void successfulLoginIssuesTokenAndResetsFailures() {
        when(encoder.matches("good", "hash")).thenReturn(true);
        when(tokens.issue(eq(user), any())).thenReturn(new TokenService.Token("jwt", 3600));
        assertThat(service.login("a@example.test", "good")).map(TokenService.Token::accessToken).contains("jwt");
        assertThat(user.getFailedLogins()).isZero();
    }

    @Test
    void locksAfterThresholdAndRejectsEvenCorrectPassword() {
        when(encoder.matches("bad", "hash")).thenReturn(false);
        for (int i = 0; i < 3; i++) {
            assertThat(service.login("a@example.test", "bad")).isEmpty();
        }
        assertThat(user.isLocked(clock.instant())).isTrue();
        when(encoder.matches("good", "hash")).thenReturn(true);
        assertThat(service.login("a@example.test", "good")).isEmpty();
        verify(tokens, never()).issue(any(), any());
    }

    @Test
    void unknownUserStillPaysBcryptCost() {
        when(users.findByEmailIgnoreCase("x@example.test")).thenReturn(Optional.empty());
        assertThat(service.login("x@example.test", "whatever")).isEmpty();
        verify(encoder).matches(eq("whatever"), anyString());
    }

    @Test
    void inactiveUserRejected() {
        user.setEmploymentStatus("INACTIVE");
        when(encoder.matches("good", "hash")).thenReturn(true);
        assertThat(service.login("a@example.test", "good")).isEmpty();
    }

    @Test
    void passwordPolicy() {
        PasswordPolicy.check("Valid-Passw0rd");
        assertThatThrownBy(() -> PasswordPolicy.check("short1A")).isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> PasswordPolicy.check("alllowercase123")).isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> PasswordPolicy.check("NoDigitsHereAtAll")).isInstanceOf(BusinessRuleException.class);
        assertThatThrownBy(() -> PasswordPolicy.check("Aa1" + "x".repeat(80))).isInstanceOf(BusinessRuleException.class);
    }
}
