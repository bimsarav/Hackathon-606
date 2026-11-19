package com.esmhub.directory.service.auth;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.core.io.Resource;

/**
 * Signing key material: PEM text via env ({@code ESM_JWT_PRIVATE_KEY}/{@code ESM_JWT_PUBLIC_KEY}) or classpath/file
 * locations (tests). If neither is set, a key pair is generated at start-up (single-instance development only).
 */
@ConfigurationProperties("esm.jwt")
public record JwtProperties(String issuer, int ttlMinutes, String privateKey, String publicKey,
                            Resource privateKeyLocation, Resource publicKeyLocation) {
    public JwtProperties {
        issuer = issuer == null || issuer.isBlank() ? "esm-hub" : issuer;
        ttlMinutes = ttlMinutes <= 0 ? 60 : ttlMinutes;
    }
}
