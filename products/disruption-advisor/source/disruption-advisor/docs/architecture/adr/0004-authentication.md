# ADR-0004: Authentication and authorization

- **Status:** Accepted for the MVP (2026-11-20). Revisit before production (phase 4).
- **Context:** Every product needs authentication (engineering standards §9.12). FastAPI has no built-in user system.
- **Options:**
  1. **OIDC with an existing identity provider (recommended)** (Keycloak, Entra ID, Auth0, Cognito, ...). The SPA uses the authorization code flow with PKCE; the API validates bearer JWTs against the provider's JWKS in a FastAPI dependency and maps roles or claims to permissions.
  2. **Self-hosted Keycloak** in Compose, when no identity provider exists but SSO, MFA or federation is required.
  3. **Local users in the API** (argon2 password hashing + httpOnly session cookie, same origin through nginx), only for small internal tools.
- **Decision (MVP):** a variant of option 3 without a user database.
  - **Accounts:** two demo roles, OCC and PCU (Q19), defined in the `DEMO_USERS` secret (server `.env`, mode 600) and compared in constant time.
  - **Tokens:** the API issues HMAC-SHA256-signed bearer tokens that expire after `TOKEN_TTL_HOURS` (`app/auth.py`, Python standard library only).
  - **Rate limit:** nginx limits sign-in to 10 attempts per minute per address.
  - **Coverage:** every `/api/v1` route except login requires a token. Tests cover wrong password, missing token and forged token.
- **Consequences:**
  - No new dependency or identity infrastructure for the demo.
  - Not suitable for production: shared role accounts, no MFA or SSO, and HTTP only until phase 2.
  - Before production: OIDC with the airline's identity provider (option 1), with per-user identities in the decision audit.
