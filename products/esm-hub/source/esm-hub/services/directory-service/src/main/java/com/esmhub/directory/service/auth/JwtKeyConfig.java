package com.esmhub.directory.service.auth;

import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

/** RSA key pair for issuing (encoder) and validating (decoder) tokens, and the public JWK set served at /.well-known. */
@Configuration(proxyBeanMethods = false)
public class JwtKeyConfig {
    private static final Logger log = LoggerFactory.getLogger(JwtKeyConfig.class);

    @Bean
    RSAKey rsaKey(JwtProperties props) throws GeneralSecurityException, IOException {
        String priv = props.privateKey();
        String pub = props.publicKey();
        if ((priv == null || priv.isBlank()) && props.privateKeyLocation() != null) {
            priv = props.privateKeyLocation().getContentAsString(StandardCharsets.US_ASCII);
            pub = props.publicKeyLocation().getContentAsString(StandardCharsets.US_ASCII);
        }
        KeyPair pair;
        if (priv == null || priv.isBlank()) {
            log.warn("ESM_JWT_PRIVATE_KEY not set: generating an ephemeral key pair (development only, tokens die on restart)");
            KeyPairGenerator gen = KeyPairGenerator.getInstance("RSA");
            gen.initialize(2048);
            pair = gen.generateKeyPair();
        } else {
            KeyFactory kf = KeyFactory.getInstance("RSA");
            pair = new KeyPair(kf.generatePublic(new X509EncodedKeySpec(der(pub))), kf.generatePrivate(new PKCS8EncodedKeySpec(der(priv))));
        }
        return new RSAKey.Builder((RSAPublicKey) pair.getPublic()).privateKey((RSAPrivateKey) pair.getPrivate())
                .keyID(props.issuer() + "-1").build();
    }

    @Bean
    JwtEncoder jwtEncoder(RSAKey key) {
        return new NimbusJwtEncoder(new ImmutableJWKSet<>(new JWKSet(key)));
    }

    /** directory-service validates its own tokens locally (no HTTP call to itself). */
    @Bean
    JwtDecoder jwtDecoder(RSAKey key) throws com.nimbusds.jose.JOSEException {
        return NimbusJwtDecoder.withPublicKey(key.toRSAPublicKey()).build();
    }

    private static byte[] der(String pem) {
        return Base64.getDecoder().decode(pem.replaceAll("-----[A-Z ]+-----", "").replaceAll("\\\\n|\\s", ""));
    }
}
