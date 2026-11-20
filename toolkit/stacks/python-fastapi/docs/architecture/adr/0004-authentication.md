# ADR-0004: Authentication and authorization

- **Status:** **Proposed: TODO-PRODUCT must decide before Phase 4.** The skeleton deliberately ships without authentication, because the identity source is product-specific.
- **Context:** Every product needs authentication (MASTER_PROMPT §9.12). FastAPI has no built-in user system.
- **Options:**
  1. **OIDC with an existing identity provider (recommended)** (Keycloak, Entra ID, Auth0, Cognito, ...). The SPA uses the authorization code flow with PKCE; the API validates bearer JWTs against the provider's JWKS in a FastAPI dependency and maps roles or claims to permissions.
  2. **Self-hosted Keycloak** in Compose, when no identity provider exists but SSO, MFA or federation is required.
  3. **Local users in the API** (argon2 password hashing + httpOnly session cookie, same origin through nginx), only for small internal tools.
- **Decision:** TODO-PRODUCT. Record the library and version in COMPATIBILITY_MATRIX.md and add tests for the authenticated and forbidden paths.
- **Consequences:** TODO-PRODUCT.
