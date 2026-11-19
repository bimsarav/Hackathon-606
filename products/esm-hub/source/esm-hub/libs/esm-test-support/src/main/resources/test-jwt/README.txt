TEST-ONLY RSA key pair used to sign JWTs in automated tests. Never use it in any environment.
Services trust it only in the `test` profile (spring.security.oauth2.resourceserver.jwt.public-key-location).
