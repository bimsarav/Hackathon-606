# Security Rules
- Deny by default: every endpoint is authenticated unless it is explicitly public (health, login). Authorisation is checked in the service, not only at the gateway.
- Auth: OAuth2/OIDC-ready JWT (Spring Security resource server); passwords bcrypt or argon2 if local accounts are needed; lockout and rate limiting on login.
- Tenant and data boundaries are enforced in every query; foreign records are reported as 404.
- Secrets only in env vars, Docker secrets or a vault; never in git, images, logs or Kafka events.
- Containers run as non-root, read-only file system where possible, minimal base images (e.g. Eclipse Temurin JRE / distroless, nginx-unprivileged).
- Supply chain: OWASP Dependency-Check (or Trivy) for Gradle and npm dependencies, plus an image scan, in CI; findings fixed or documented.
- Security headers and CSP on the frontend; CSRF considered for any cookie-based auth.
- A threat model (STRIDE) and security test report in the product repo's `docs/security/`.
