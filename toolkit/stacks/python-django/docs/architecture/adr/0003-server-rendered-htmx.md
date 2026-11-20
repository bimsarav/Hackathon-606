# ADR-0003: Server-rendered UI with Django templates and htmx

- **Status:** Accepted (profile default)
- **Context:** Business UIs are mostly forms, lists and detail pages. A separate SPA adds a second toolchain, an API contract to keep in sync, and client-side state (§9.4: "avoid unnecessary client-side complexity").
- **Decision:** Django templates for pages and htmx 2 (vendored, no Node build) for partial updates. CSRF is sent through `hx-headers`, and validation errors come back as re-rendered form fragments (HTTP 422). The REST API (DRF) stays available for integrations and future clients.
- **Consequences:** One runtime, no frontend build, fast delivery, and accessible HTML by default. Highly interactive screens would need a component framework. If several are needed, choose the python-fastapi + React profile instead (new ADR).
