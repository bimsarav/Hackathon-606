package com.esmhub.directory.service.auth;

import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** Public keys for resource servers (all other services validate tokens with this). */
@RestController
public class JwksController {
    private final Map<String, Object> jwks;

    public JwksController(RSAKey key) {
        this.jwks = new JWKSet(key.toPublicJWK()).toJSONObject();
    }

    @GetMapping("/.well-known/jwks.json")
    public Map<String, Object> jwks() { return jwks; }
}
