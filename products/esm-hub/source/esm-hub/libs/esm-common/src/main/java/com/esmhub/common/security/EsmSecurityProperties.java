package com.esmhub.common.security;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** {@code esm.security.public-paths}: extra unauthenticated paths of a service (e.g. login, JWKS). */
@ConfigurationProperties("esm.security")
public record EsmSecurityProperties(List<String> publicPaths) {
    public EsmSecurityProperties {
        publicPaths = publicPaths == null ? List.of() : List.copyOf(publicPaths);
    }
}
