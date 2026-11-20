# ADR-0004: Authentication and authorization

- **Status:** Accepted (profile default). TODO-PRODUCT: confirm or replace.
- **Context:** Every product needs authentication; the identity source is product-specific (local users, corporate SSO, customers).
- **Decision (default):** Django's built-in auth: database sessions, PBKDF2 password hashing, 12-character minimum length, CSRF protection, secure cookies behind TLS. The API uses `SessionAuthentication` and `IsAuthenticated` by default. Object-level access is enforced in querysets (see `apps/notes/views.py`). Roles use Django groups and permissions.
- **When to replace:** If the organisation has an identity provider, add OIDC login (for example `mozilla-django-oidc` or `django-allauth`) with an ADR and update the compatibility matrix; keep Django sessions for the browser.
- **Consequences:** Secure defaults with no extra infrastructure; SSO is an additive change.
