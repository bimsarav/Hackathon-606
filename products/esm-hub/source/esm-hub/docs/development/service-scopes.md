# Service Scopes (implementation checklist)

Functional spec: a previous Python product with the same rules, at
`/home/heshawa/AI-projects-personal/hack-isa/backup-1training/Hackathon-606/source/backend/app/`. Paths below are relative to it.
Tests to mirror are in `../../tests/`. Conventions: `docs/development/service-playbook.md`. Contracts: `docs/architecture/event-contracts.md`.

| Service | Port, DB | Spec files | Must have |
|---|---|---|---|
| incident-service | 8082, esm_incident | services/sla.py, services/incidents.py, routers/incidents.py, worker.py (scan_sla, auto_close), routers/problems_changes.py (problems), routers/admin.py (priorities, SLA, calendars, rules) | Business-hours SLA engine with every test_sla.py case; lifecycle, RBAC, reopen window, assignment rules (replica), pause/resume; problems; scheduled escalation (deduped) and auto-close; `incident.incidents` + `incident.problems` snapshots; `incident.events` with NotificationIntent; seed: priorities, statuses, SLA policies, 150 incidents, comments, worklogs, problems, links |
| request-service | 8083, esm_request | services/approvals.py, routers/requests.py, cli.py DEMO_CONFIG | Catalogue + steps, requests, sequential cost-conditional approvals (manager from replica, SoD, 409 on re-decision), fulfil, `GET /approvals`, `POST /approvals/{id}/decision`; `request.requests` + `request.events`; seed 45 requests, catalogue, pending approvals |
| change-service | 8084, esm_change | routers/problems_changes.py (changes), services/approvals.py (change policy) | Change lifecycle, assessment completeness, policy (STANDARD pre-approved; CHANGE_MANAGER; HIGH NORMAL + SERVICE_MANAGER), plan lock, implement/close RBAC, `/changes-calendar`, `GET /change-approvals`, `POST /change-approvals/{id}/decision`; `change.changes` + `change.events`; seed 20 changes + pending approvals |
| asset-service | 8085, esm_asset | routers/assets_kb.py (assets) | Lifecycle + history, warranty state, filters, export, employees see own; `asset.assets` + `asset.events`; seed 60 assets + history |
| knowledge-service | 8086, esm_knowledge | routers/assets_kb.py (KB) | Four-eyes workflow, FTS search (websearch_to_tsquery, GIN), idempotent feedback, editors notified; `knowledge.events`; seed 15 articles |
| audit-service | 8088, esm_audit | routers/ops.py (audit), 0002 trigger | Consume `audit.events` (EventReader.once), append-only `audit_records` (trigger blocks UPDATE/DELETE), `GET /api/v1/audit` + `/export` (AUDITOR/ADMIN, audited), declares `audit.events` topic; seed 80 legacy audit logs |
| notification-service | 8087, esm_notification | worker.py (dispatch), routers/ops.py (notifications) | Consume *.events DomainEvent → in-app + email per recipient (dedupe), email sender with backoff → DEAD, admin retry, inbox API; seed 60 notifications |
| reporting-service | 8089, esm_reporting | routers/reports.py | Consume state topics into projections (tombstones delete); summary, incident-volume (8 dims), sla-compliance, backlog-ageing, workload, assets, requests, changes, problems, CSV export; RBAC; no seed (data comes from snapshots) |

Every service needs:
- unit tests (JUnit 5 + Mockito) for its rules
- Testcontainers ITs covering the happy path, RBAC denial, tenant isolation (404) and a Kafka round trip
- `tools/seed/queries/<service>.sql` + `tools/seed/export.sh <service>`, verified on a scratch DB (where a seed applies)
- a green `:services:<service>:build`
