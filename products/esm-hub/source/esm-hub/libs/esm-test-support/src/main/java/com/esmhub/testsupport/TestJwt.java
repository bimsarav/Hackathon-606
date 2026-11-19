package com.esmhub.testsupport;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.interfaces.RSAPrivateKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.time.Instant;
import java.util.Arrays;
import java.util.Base64;
import java.util.Date;
import java.util.List;

/** Mints JWTs exactly like directory-service, signed with the TEST-ONLY key (classpath:test-jwt/private.pem). */
public final class TestJwt {
    private static final RSAPrivateKey KEY = loadKey();

    private TestJwt() {}

    /** "Bearer ..." header value for a user of company {@code companyId} with the given roles and no teams. */
    public static String bearer(long userId, long companyId, String... roles) {
        return "Bearer " + token(userId, companyId, List.of(), roles);
    }

    public static String bearer(long userId, long companyId, List<Long> teamIds, String... roles) {
        return "Bearer " + token(userId, companyId, teamIds, roles);
    }

    public static String token(long userId, long companyId, List<Long> teamIds, String... roles) {
        Instant now = Instant.now();
        JWTClaimsSet claims = new JWTClaimsSet.Builder()
                .subject(String.valueOf(userId)).issuer("esm-hub-test")
                .issueTime(Date.from(now)).expirationTime(Date.from(now.plusSeconds(3600)))
                .claim("cid", companyId).claim("roles", Arrays.asList(roles)).claim("teams", teamIds)
                .claim("name", "Test User " + userId).claim("email", "user" + userId + "@example.test")
                .build();
        try {
            SignedJWT jwt = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).keyID("test").build(), claims);
            jwt.sign(new RSASSASigner(KEY));
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new IllegalStateException(e);
        }
    }

    private static RSAPrivateKey loadKey() {
        try (InputStream in = TestJwt.class.getResourceAsStream("/test-jwt/private.pem")) {
            String pem = new String(in.readAllBytes(), StandardCharsets.US_ASCII)
                    .replaceAll("-----[A-Z ]+-----", "").replaceAll("\\s", "");
            return (RSAPrivateKey) KeyFactory.getInstance("RSA")
                    .generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(pem)));
        } catch (IOException | GeneralSecurityException e) {
            throw new IllegalStateException("cannot load test JWT key", e);
        }
    }
}
