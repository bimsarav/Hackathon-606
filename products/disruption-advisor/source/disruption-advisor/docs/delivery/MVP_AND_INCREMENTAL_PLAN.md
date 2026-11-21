# MVP and Incremental Deployment Plan

Delivery cadence (user instruction 2026-11-20): design first, MVP first, host the MVP, then incremental phases. **Each phase after the MVP starts only with explicit user approval.** Phase status is tracked in the table below.

| Phase | Content | Status |
|---|---|---|
| 0 Design | Architecture and diagrams ([SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md)) | Done 2026-11-20 |
| 1 MVP | Scenarios A and B end to end, hosted | Done 2026-11-20: deployed and verified, incl. reboot test |
| 2 Predict | Delay-risk prediction, 7-day watchlist, misconnect risk per passenger | Approved 2026-11-21; deployed (reboot check skipped by user) |
| 3 Agent and what-if | Agentic orchestration; cancellation and consolidation as recovery options; strategy comparison | Needs approval |
| 4 Extend | Equipment change, bus legs, crew, real data feeds, production hardening | Needs approval |
| 6 Secure and protect | HTTPS (Caddy, sslip.io) and nightly PostgreSQL backup with a restore test (moved from phase 2 by the user, 2026-11-21) | Needs approval |

## Phase 1 — MVP (approved)
**Goal:** the briefing's ask: *"Pick one or two realistic disruption scenarios. Show how the AI agent identifies impact, evaluates the available recovery, and recommends an action"*, with explanations.

**In scope**
1. **Data ingest:**
   - All supplied extracts go into `ops.duckdb`: rotation 19–30 Nov 2026, active bookings in that window, inventory, MCT and airport time zones.
   - Labelled synthetic enrichment: loyalty tier, fare family, SSRs, aircraft registry.
   - Mismatches are recorded, never fatal.
2. **Scenario A (inbound delay):**
   - Pick any flight (preset: a delayed inbound to SHJ, 120–180 min).
   - The system shows downstream legs on the same aircraft with new times over 7 days, misconnecting passengers, and the delay cost.
3. **Recovery options (2 levers, Q27/Q28):**
   - (1) Absorb the delay along the rotation.
   - (2) Swap in a same-type aircraft that is free at the station.
   - Each option shows delay minutes, passengers affected, misconnects and cost, and the options are ranked.
4. **Scenario B (cancellation with too few seats):**
   - Affected passengers are ranked by strict tiers, then a weighted score, with per-attribute reasons.
   - OR-Tools CP-SAT assigns them to alternatives (same O&D or a legal SHJ connection, within 24 h) using real seat availability, keeping PNRs together.
   - Anyone left over is shown with next-day + hotel care.
5. **Configurable weights:** sliders re-run the ranking and the rebooking plan (what-if).
6. **Explanations and messages:**
   - The Claude API turns the machine reasons into plain English and drafts English passenger messages.
   - A deterministic template is used if the API is unavailable.
   - No names or contact details are sent to the API.
7. **Human in the loop:** approve or reject each recommendation; every decision is audited in PostgreSQL.
8. **Access:** login with two demo roles (OCC, PCU).
9. **Hosting:**
   - OCI server, `http://92.5.154.198:8888`.
   - Docker Compose with `restart: unless-stopped`, Docker enabled at boot.
   - Health checks, log rotation, memory limits.
   - A reboot test is performed and recorded (engineering standards §14).
10. **Tests:** pytest (engine rules, API, Testcontainers PostgreSQL), Vitest (UI), Playwright (both scenarios against the composed stack), Trivy scans.

**Out of scope for the MVP** (later phases):
- Delay prediction.
- Cancellation, consolidation or equipment change as *recommended* options.
- Crew legality.
- Bus legs.
- HTTPS.
- Backups beyond the PostgreSQL volume.
- CI/CD deployment.

**Done when:**
- `scripts/check.sh` passes.
- Playwright passes for both scenarios against the composed stack and against the hosted URL.
- The reboot test passes.
- The URL and logins are sent to the user.

## Phase 2 — Predict (approved by the user 2026-11-21)
- LightGBM delay-risk model trained on the Jan–Nov 2026 punctuality data, using only what is known 7 days ahead (stations, departure hour and weekday, aircraft type, position in the aircraft's day, turn buffer, load factor, recent station/route/network delay rates). Details: `docs/testing/model-card.md`.
- Probability of a departure delay of 5, 15, 30, 60, 120 and 180 min or more per upcoming flight, with plain-language reasons from TreeSHAP.
- A 7-day "at risk" watchlist that feeds Scenario A automatically.
- Per-passenger misconnect risk.
- (HTTPS and nightly backups moved to phase 6 by the user, 2026-11-21.)

## Phase 3 — Agent and what-if (needs approval)
- A Claude tool-using agent that coordinates the impact, recovery, priority and rebooking modules and explains its chain of reasoning. It stays recommend-only.
- More recovery options: cancel or consolidate and protect passengers.
- Side-by-side strategy comparison (for example "protect most passengers" vs "lowest cost" vs "least delay").

## Phase 4 — Extend (needs approval)
- **Unaccompanied minors (future enhancement, removed from MVP scope 2026-11-21):** UMNR identification, mandatory priority (EU261 Art. 11), supervision during long waits, guardian notification, and handover rules.
- **Partner and other carriers (future enhancement, removed from MVP scope 2026-11-21):** bring the group and partner carriers in the extracts (3L, 3O, E5, 9P, 4P) back into the operating picture (`OPERATING_CARRIERS`). That covers their flights as rebooking alternatives (interline and group re-accommodation, with bilateral agreements), their aircraft as swap candidates, and cross-carrier connections.
- Equipment change (different type or capacity) and bus + air journeys.
- Crew legality, when crew data exists.
- Replace synthetic data with real loyalty, SSR, fare-family and aircraft files as they arrive.
- CI/CD deployment, monitoring and alerting, and the full §14 operations baseline.

## Phase 6 — Secure and protect (needs approval; moved from phase 2 by the user, 2026-11-21)
No phase 5 is defined yet.
- HTTPS through Caddy and Let's Encrypt on a free sslip.io hostname, with `:8888` kept (design: ADR 0009).
- Nightly PostgreSQL backup with a restore test (design: ADR 0009).

## Deployment procedure (every phase)
1. Plan the phase and get user approval.
2. Build and run `scripts/check.sh`.
3. Run Playwright locally.
4. Run the Trivy scans.
5. Tag the images, deploy (copy the tree to the server and run `docker compose up -d --build`, see `docs/deployment/DEPLOYMENT_GUIDE.md`; take a manual `pg_dump` of the database first; automated nightly backups come in phase 6), and run migrations.
6. Verify (engineering standards §13.9): health checks, Playwright against the server URL, and the logs.
7. Rollback = redeploy the previous image tag. The rollback steps are in the runbook.
8. Report the URL and results, update the phase status table above, and wait for approval of the next phase.
