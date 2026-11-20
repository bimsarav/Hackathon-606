# Adding a stack profile (contract)

Build a profile only when a product selects a stack that no profile covers. Build it **as** the product's starting point, so the cost is paid once. Copy the closest existing profile and adapt it. Every profile must have:

| File | Requirement |
|---|---|
| `PROFILE.md` | Menu summary (3–4 lines) and a table with **all** §9.16.2 fields, fit/avoid, advantages, limitations, complexity, maintainability |
| `freshness.conf` | `<endoflife.date product> <release line> <pinned version>` per runtime/framework/database line; `hold <package> <reason>` for deliberate major-version holds |
| `docs/architecture/` | `SYSTEM_ARCHITECTURE.md`, `TECH_STACK.md`, `TECHNOLOGY_COMPARISON.md` (with `TODO-PRODUCT` markers), `COMPATIBILITY_MATRIX.md` (all 8 columns, real versions), `adr/0001-stack-profile.md` + one ADR per major default |
| `skeleton/` | A working repository using the sample identifiers `sample-app` / `sample_app` / `Sample App` (renamed by `scripts/new-product.sh`). Keep identifier-bearing lines short, so long product names do not break line-length rules |
| `skeleton/compose.yml` | First line `name: sample-app` (scripts derive image and volume names from it); full stack with a one-shot migrate service and healthchecks |
| `skeleton/scripts/check.sh` | Runs in Docker; subcommands `all` (default) / `lock` / `outdated`; one `PASS`/`FAIL <step>` line per step, logs in `logs/` |
| `skeleton/scripts/smoke.sh` | Builds the images, starts Compose, checks the public endpoints and container health, tears down; exit 0 only if all pass |
| `skeleton/README.md`, `.github/workflows/ci.yml`, `.env.example`, `.gitignore` | Build/test/deploy without AI; CI runs check, smoke and Trivy; no secrets |
| Images | Multi-stage, pinned base tags, non-root user, healthcheck, OS updates applied, no build tools at runtime |

Done means: `scripts/verify-profile.sh <profile>` reports PASS (gate, smoke, Trivy fs and images with 0 fixable HIGH/CRITICAL), `scripts/check-stack-freshness.sh <profile>` reports FRESH, and the profile is listed in `../README.md`.
