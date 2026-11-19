package com.esmhub.directory.service.auth;

import com.esmhub.directory.service.user.User;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

/** Issues the platform access token (claims documented in docs/architecture/architecture.md §4). */
@Service
public class TokenService {
    private final JwtEncoder encoder;
    private final JwtProperties props;

    public TokenService(JwtEncoder encoder, JwtProperties props) {
        this.encoder = encoder;
        this.props = props;
    }

    public record Token(String accessToken, long expiresIn) {}

    public Token issue(User u, List<Long> teamIds) {
        Instant now = Instant.now();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(props.issuer()).subject(String.valueOf(u.getId()))
                .issuedAt(now).expiresAt(now.plus(props.ttlMinutes(), ChronoUnit.MINUTES))
                .claim("cid", u.getCompanyId()).claim("roles", List.copyOf(u.roleNames())).claim("teams", teamIds)
                .claim("name", u.fullName()).claim("email", u.getEmail())
                .build();
        String jwt = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(SignatureAlgorithm.RS256).build(), claims)).getTokenValue();
        return new Token(jwt, props.ttlMinutes() * 60L);
    }
}
