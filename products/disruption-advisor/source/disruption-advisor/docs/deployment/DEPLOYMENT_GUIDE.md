# Deployment Guide

This guide covers the target host, how the MVP and phase 2 (Predict) are deployed, how it survives a reboot, and how to roll back. Architecture and diagrams are in [../architecture/SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md) §8. The phase plan, with an approval gate per phase, is in [../delivery/MVP_AND_INCREMENTAL_PLAN.md](../delivery/MVP_AND_INCREMENTAL_PLAN.md). No secret values appear in this document.

## Target
| Item | Value |
|---|---|
| Host | OCI VM (eu-frankfurt-1), x86_64, 8 vCPU, 62 GiB, Oracle Linux 10, Docker 29 + Compose v5, firewalld |
| URL | `http://<server>:8888`. HTTP only; HTTPS is planned for phase 6 (needs approval) |
| Published ports | 8888 (`web`) only. PostgreSQL and the API are reachable only on the Compose network |
| Paths on the host | Code: `~/apps/disruption-advisor` · extracts (read-only mount): `~/disruption-advisor-input` (mode 700) · secrets: `~/apps/disruption-advisor/settings.env` (mode 600; `.env` is a link to it for Docker Compose) |
| Data | Docker volumes `disruption-advisor_db-data` (PostgreSQL: scenarios, decisions) and `disruption-advisor_ops-data` (Parquet built by `ingest`, including the phase 2 delay-risk outputs) |

## First deployment
1. **Copy the repository** to the host. Exclude `settings.env`, `.env`, `node_modules`, `logs` and build output.
2. **Copy the extracts** to the input folder (`scp`).
3. **Create `settings.env`** with `scripts/init-settings.sh` and fill it with new random values: database password, `TOKEN_SECRET`, `DEMO_USERS` passwords, `ANTHROPIC_API_KEY`. Set `WEB_PORT=8888` and `INPUT_DIR` to the input folder, (the script sets mode 600).
4. **Build and start:** `docker compose build && docker compose up -d`. The first `ingest` takes about 4 minutes.
   - Ingest **stage 3** (phase 2) trains the delay-risk model and scores the window. It takes about 30 s on the server and writes `flight_risk.parquet`, `connection_risk.parquet` and `model_card.json` into the ops volume. It reruns whenever stage 2 reruns (new extracts, options or build code), so every data drop retrains the model. Without these files the risk endpoints answer 503 and the rest of the app works as before.
5. **Verify** (engineering standards §13.9):
   - `scripts/smoke.sh http://<server>:8888`
   - `E2E_BASE_URL=http://<server>:8888 scripts/e2e.sh`, run from a workstation with Docker
   - `docker compose ps` shows `api` and `web` as healthy
   - `docker compose logs ingest` shows `stage 3 done`, and the "Delay watchlist (7 days)" tab lists flights
   - `docker compose logs api` shows no errors

## Restart resilience (engineering standards §14)
- **Docker starts at boot:** `systemctl is-enabled docker` returns `enabled`.
- **Services restart by themselves:** `db`, `api` and `web` use `restart: unless-stopped`. After a reboot the Docker daemon restarts only these three. The one-shot `migrate` and `ingest` jobs do not run again, and need not, because their results persist in the `db-data` and `ops-data` volumes. They run on every `docker compose up`, and `ingest` skips the work when the inputs are unchanged.
- **Startup order is based on readiness, not container start:** the database must be healthy, `migrate` and `ingest` must complete, and `api` must be healthy (database plus operating data loaded) before `web` starts. Compose enforces this order on `docker compose up`. After a reboot the daemon starts the containers without that ordering, which is safe because the API connects to PostgreSQL lazily (pool pre-ping) and `/health/ready` reports DOWN until the database answers.
- **Limits:**
  - memory: `db` 1 GB, `api` 3 GB, `ingest` 8 GB, `web` 256 MB;
  - JSON logs rotate at 10 MB × 5 files per container.
- **Phase 2 reboot test: not done yet** (pending user approval). Until it passes, phase 2 is reported as deployed with operational verification pending. Use the steps below.
- **Reboot test, 2026-11-20 (PASSED, phase 1 stack):**
  - `sudo systemctl reboot` at 19:55:41Z; SSH was back after about 50 s.
  - Docker was active, and `db`, `api` and `web` were healthy 30 s after boot with no manual action.
  - Data survived: all 4 scenarios and 2 decisions stored before the reboot were present afterwards.
  - Smoke test 11/11 and Playwright 3/3 passed against the public URL after the reboot.
  - To repeat: `sudo reboot`, wait, check `docker compose ps`, then run the smoke and end-to-end tests again.

## Update and rollback
- **Update:**
  1. Copy the new code.
  2. Run `docker compose build`.
  3. Run `docker compose up -d`.

  Migrations run automatically.
- **Rollback:** before each update, tag the running images, for example `docker tag disruption-advisor-api:latest disruption-advisor-api:rollback` (same for `web`). To roll back, retag `:rollback` as `:latest` and run `docker compose up -d`.
- **Database backup (manual in the MVP):**
  - back up with `docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql`;
  - restore with `psql`.

  Take this manual dump before every deployment. Nightly automated backups with a restore test are planned for phase 6 (needs approval; design in ADR 0009).

## Known limitations
- **No HTTPS yet (phase 6).** Do not reuse the demo passwords anywhere else.
- **No automated backup yet (phase 6).** Only the manual `pg_dump` above.
- **Demo sign-in only:** two roles held in `settings.env`. Production would use the airline's identity provider (ADR 0004).
- **Assumed data:** synthetic loyalty, fare-family and special-service data, and assumed costs, all labelled in the UI.
- **Crew legality is not checked:** no crew data was supplied.
- **Simulated clock:** the demo "now" is 2026-11-20 00:00 UTC (`NOW_UTC`).
