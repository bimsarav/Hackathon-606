# Stack profile catalogue

Source of options for the Technology Selection Checkpoint (MASTER_PROMPT §9.16.2). Offer the 2–5 profiles that fit the analysed domain (§9.17), plus "Let the AI Agent Decide" last. A domain that no profile fits gets a **new** option (and, once selected, a new profile: see [_template/README.md](_template/README.md)). Never force-fit an existing profile.

| Profile | Summary | Fits (§9.17) | Complexity | Status |
|---|---|---|---|---|
| [python-django](python-django/PROFILE.md) | Django 5.2 LTS modular monolith, DRF API, server-rendered htmx UI, PostgreSQL 18 | Enterprise/business management, internal tools, admin-heavy portals, CRUD-rich apps, fast MVPs | Low | [VERIFIED.md](python-django/VERIFIED.md) |
| [python-fastapi](python-fastapi/PROFILE.md) | FastAPI + SQLAlchemy 2 + Alembic API, React 19 + TypeScript SPA behind nginx, PostgreSQL 18 | API-first/SaaS, rich interactive UIs, integration hubs, AI/data-adjacent services, mobile backends | Medium | [VERIFIED.md](python-fastapi/VERIFIED.md) |

Not yet built (build when a product first selects one, then add it here): Java Spring (modular monolith or microservices; esm-hub's stack, extract after its delivery), PHP Laravel, PHP Symfony, Node NestJS, .NET ASP.NET Core.

## Using a profile for a product
1. `scripts/check-stack-freshness.sh <profile>`: if it reports ACTION NEEDED, bump the versions (ADR in the profile's `docs/architecture/adr/`, plus `pyproject.toml`/`package.json`, Dockerfiles, `COMPATIBILITY_MATRIX.md` and `freshness.conf`), then run `scripts/verify-profile.sh <profile>`.
2. Write the options into the product's `TECHNOLOGY_COMPARISON.md` first, then show the numbered menu (use each `PROFILE.md` "Menu summary").
3. After the selection: `scripts/new-product.sh <profile> <product-name>`. Fill the `TODO-PRODUCT` parts of the copied `docs/architecture/*.md` and record the selection (§9.16.7).
4. The Technology Selection Gate's compatibility proof is the product's own `scripts/check.sh` (+ `scripts/smoke.sh`) passing on the generated copy.

## Maintenance
- Re-verify a profile when its `VERIFIED.md` is older than 30 days and it is about to be used, and after any change to it.
- Improvements found while building a product (bug fixes, missing hardening) go back into the profile, followed by `scripts/verify-profile.sh`.
- Delivered products keep their own pinned copy. A profile update never changes them.
