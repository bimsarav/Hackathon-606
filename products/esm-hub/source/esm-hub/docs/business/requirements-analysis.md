# ESMP Requirements Analysis

Sources: `input/requirements/PROBLEM_STATEMENT.md` (PS), `input/requirements/DATA_DICTIONARY.md` (DD), `input/data/esmp_sample_dump.sql` (dump).
Every requirement below traces back to one of these sources. Defaults for open business rules are labelled **DEFAULT (pending PO approval)**. Each one is configurable, so changing it means editing data, not code.

## 1. Business objective
Northstar Holdings (Abu Dhabi, Dubai, London, Colombo) wants one secure, multi-office platform to replace email, phone and spreadsheet tracking. It must centralise service delivery, automate workflows (SLA, approvals, notifications) and give trustworthy analytics (PS §2–3).

## 2. Personas and roles
| Persona (PS §4) | Seed role (dump) | Main capabilities |
|---|---|---|
| Employee | EMPLOYEE | Raise and track own incidents and requests; search the KB; give KB feedback; reopen own resolved incidents |
| Service desk agent | SERVICE_DESK_AGENT | Triage all incidents in their company: classify, prioritise, assign |
| Resolver/technician | TECHNICIAN | Work assigned/team tickets: comment, worklog, resolve |
| Team lead | TEAM_LEAD | Queue/workload views, reassignment, escalations, team reports |
| Service manager | SERVICE_MANAGER | Services, catalogue, SLA policies, calendars, reports |
| Change manager | CHANGE_MANAGER | Assess and approve changes, schedule and track them |
| Asset manager | ASSET_MANAGER | Inventory, assignment history, warranty, lifecycle |
| Knowledge editor | KNOWLEDGE_EDITOR (dump only) | Review and publish articles |
| Auditor | AUDITOR | Read-only audit trail and reports |
| Platform admin | ADMIN | Users, roles, reference data, configuration |

## 3. Functional requirements (PS §5)
| ID | Requirement | Scope delivered |
|---|---|---|
| FR-1 | Authentication, profile, RBAC | Local login (bcrypt hashes, RS256 JWT issued by directory-service), `/me`, role-guarded endpoints. External IdP is a pending question (BQ-9) |
| FR-2 | Company, office, department hierarchy | Read APIs plus admin create/update. Data scoped by company |
| FR-3 | Incident lifecycle | Create, classify, prioritise, assign, comment (public/internal), worklog, resolve, close, reopen, cancel. Transitions are checked against a workflow table |
| FR-4 | Service request catalogue and approvals | Catalogue items per service; configurable approval steps (sequential, conditional on cost); approve/reject; fulfil |
| FR-5 | SLA policies, clocks, calendars, pause, escalation | Per priority/service SLA with versioning; office business-hours calendars and holidays; pause on configured statuses; breach/at-risk escalation |
| FR-6 | Team queues, workload, assignment rules | Queue views per team; workload by assignee; rules (service → team) applied on create |
| FR-7 | Problem management | Problems, incident links, root cause, workaround, known-error flag |
| FR-8 | Change management | Risk, impact, approvals, schedule, implementation timestamps, rollback plan, status workflow |
| FR-9 | Asset inventory | CRUD, assignment history table, warranty expiry, lifecycle status |
| FR-10 | Knowledge base | Draft → review → published workflow; full-text search; helpful/not-helpful feedback |
| FR-11 | Notifications | Transactional outbox, worker with exponential backoff and an idempotency key; delivery status; in-app list |
| FR-12 | Audit trail | Append-only audit rows (actor, entity, old/new values, IP, correlation ID) for sensitive and business changes |
| FR-13 | Dashboards and reports | SLA compliance, volume, ageing, reopen rate, backlog, workload, asset estate, request costs |
| FR-14 | Search, filter, paginate, export | Filter and paginate on every list; CSV export for authorised roles |
| FR-15 | Admin configuration | Priorities, statuses, categories, services, teams, SLA policies, calendars, assignment rules |

## 4. Non-functional requirements (PS §6)
| ID | Requirement | Approach |
|---|---|---|
| NFR-1 | Secure by default, least privilege, company boundaries | Deny-by-default RBAC dependency; every query filtered by the caller's company |
| NFR-2 | Responsive web UI and documented REST API | Responsive React SPA; OpenAPI 3 per service (springdoc) |
| NFR-3 | Relational integrity, migration-based schema | PostgreSQL FKs and CHECKs; Flyway migrations per service (database-per-service) |
| NFR-4 | Structured logs with correlation IDs, no secrets | JSON logs; `X-Request-ID` propagated; ticket bodies never logged |
| NFR-5 | Health/readiness, metrics, central error handling | `/health/live`, `/health/ready`, Prometheus `/metrics`, RFC 7807-style error body |
| NFR-6 | Unit, integration, API-contract, E2E tests | JUnit 5 + Mockito (unit), Testcontainers (PostgreSQL, Kafka) integration, OpenAPI contract snapshots, Playwright E2E |
| NFR-7 | Containerised local deployment and production path | Docker Compose; production guide (TLS proxy, managed PG) |
| NFR-8 | Backup, restore, retention, DR | `pg_dump` scripts, restore runbook, retention job (configurable) |
| NFR-9 | Accessibility and keyboard navigation | Semantic HTML, labels, focus styles, skip link, ARIA live regions |
| NFR-10 | Configurable timezone and calendars; consistent timestamps | All `TIMESTAMPTZ` stored in UTC; per-office calendars with IANA timezones |
| NFR-11 | Idempotent retryable operations | `Idempotency-Key` header on create endpoints; outbox `dedupe_key` |

## 5. Business-rule questions (PS §7) and defaults in use
| ID | Question | Default in use (configurable) | Where to change |
|---|---|---|---|
| BQ-1 | SLA clock: calendar or business hours? Which holidays and timezones? | Business hours when the policy says `business_hours_only` (all seed policies do). Each office's own calendar and timezone apply; seed calendars are Mon–Fri (UAE 08:00–17:00, London 09:00–17:30, Colombo 08:30–17:00) with a sample holiday list | `business_calendars`, `calendar_holidays` |
| BQ-2 | When does the SLA pause? | While the status is `PENDING_USER` (status flag `pauses_sla`) | `ticket_statuses.pauses_sla` |
| BQ-3 | Who can change priority, requester, assignee, resolution? | Priority: agent, team lead, service manager. Requester: agent. Assignee: agent, team lead (technician can self-assign within own team). Resolution: assignee or their team lead | incident-service policy class |
| BQ-4 | Can closed tickets reopen? Within what period? | Resolved tickets can be reopened by the requester or an agent within 7 days. Closed and cancelled tickets cannot be reopened. Resolved tickets auto-close after 3 days | incident-service config `esm.incident.reopen-window-days`, `auto-close-days` |
| BQ-5 | Approvals: sequential, parallel or conditional? | Sequential steps per catalogue item; a step applies only when the request cost reaches its `min_cost` threshold. Approver is the requester's line manager or a named role | `approval_steps` |
| BQ-6 | Data retention and deletion | Keep everything; audit logs are append-only. A retention job exists but is disabled (`RETENTION_DAYS` unset) | settings |
| BQ-7 | Are offices separate legal entities? | No. Offices are locations; the **company** is the data boundary | ADR-0003 |
| BQ-8 | Mandatory notification channels | In-app (always) and email (SMTP when configured; otherwise logged as delivered to a local sink) | settings `SMTP_*` |
| BQ-9 | Integrations and identity provider | None given. Local accounts with an OIDC-ready token design; no external calls | ADR-0002 |
| BQ-10 | Availability, RTO, RPO | Target 99.5%, RTO 4 h, RPO 24 h (daily `pg_dump`); WAL archiving documented for a tighter RPO | runbooks |

## 6. Constraints and dependencies
- PostgreSQL 15+ (PS/README). The dump uses schema `esmp`.
- The supplied dump has syntax defects (see data-quality report §1). Its data is converted, with the defects repaired, into per-service demo seed migrations (`tools/seed/`).
- No credentials or external integrations supplied, so no live email provider and no SSO.
