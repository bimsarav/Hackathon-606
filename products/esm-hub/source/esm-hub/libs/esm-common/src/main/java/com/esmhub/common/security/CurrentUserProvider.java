package com.esmhub.common.security;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;

/** Reads {@link CurrentUser} from the security context (claims: sub, cid, roles, teams, name, email). */
public class CurrentUserProvider {

    public Optional<CurrentUser> find() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth instanceof JwtAuthenticationToken token) {
            return Optional.of(fromJwt(token.getToken()));
        }
        return Optional.empty();
    }

    public CurrentUser get() {
        return find().orElseThrow(() -> new IllegalStateException("No authenticated user in context"));
    }

    public static CurrentUser fromJwt(Jwt jwt) {
        Set<String> roles = new LinkedHashSet<>(strings(jwt.getClaim("roles")));
        Set<Long> teams = new LinkedHashSet<>();
        Object t = jwt.getClaim("teams");
        if (t instanceof Collection<?> c) {
            c.forEach(v -> teams.add(Long.valueOf(String.valueOf(v))));
        }
        Object cid = jwt.getClaim("cid");
        return new CurrentUser(Long.parseLong(jwt.getSubject()), cid == null ? 0L : Long.parseLong(String.valueOf(cid)),
                Set.copyOf(roles), Set.copyOf(teams), jwt.getClaimAsString("name"), jwt.getClaimAsString("email"));
    }

    static List<String> strings(Object claim) {
        if (claim instanceof Collection<?> c) {
            return c.stream().map(String::valueOf).toList();
        }
        return List.of();
    }
}
