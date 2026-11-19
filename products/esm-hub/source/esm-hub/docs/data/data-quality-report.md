# Data Profiling and Quality Report: `esmp_sample_dump.sql`

Method: the dump was loaded into PostgreSQL 16 (container), then profiled with SQL. Queries are in `tools/profiling/profile.sql`; rerun them with `tools/profiling/run_profile.sh`. Run date: 2026-11-19.

## 1. Load defects (blocking)
| # | Location | Defect | Fix applied by the seed generator (`tools/seed/`) |
|---|---|---|---|
| L1 | `priorities` insert (line ~196) | Names unquoted: `(1,P1,15,240)` | Quote them: `'P1'` |
| L2 | `ticket_statuses` insert (line ~201) | Names unquoted: `(1,NEW,False)` | Quote them: `'NEW'` |
| L3 | `sla_policies` insert (line ~352) | Python `None` instead of `NULL` | Replace with `NULL` |
| L4 | All tables with explicit IDs | `BIGSERIAL` sequences are not advanced, so the next insert fails with a duplicate key | `setval` on every sequence after load |

The original file is kept unchanged in `input/data/`.

## 2. Volumes
companies 1 · offices 4 · departments 6 · users 40 · roles 10 · user_roles 40 · teams 8 · team_members 48 · categories 5 · services 10 · priorities 4 · statuses 7 · sla_policies 4 · assets 60 · incidents 150 · comments 297 · worklogs 150 · service_requests 45 · approvals **0** · problems 12 · incident_problem_links 37 · change_requests 20 · knowledge_articles 15 · notifications 60 · audit_logs 80.
Incident dates: 2026-01-07 to 2026-11-17.

## 3. Data-quality findings
| # | Finding | Count | Impact | Handling |
|---|---|---|---|---|
| Q1 | Comment `created_at` earlier than its incident's `created_at` (up to 298 days earlier) | 140 of 297 | Breaks timelines and response-time metrics | Flagged in `dq_issues` view; first response comes from `first_response_at`, not comments |
| Q2 | Worklog `logged_at` earlier than its incident | 82 of 150 | Effort reporting is unreliable by period | Same as Q1 |
| Q3 | Incident assignee is not a member of the assigned team | 119 of 150 | Workload per team is wrong | The new API enforces membership; legacy rows are reported |
| Q4 | Assignee holds only the EMPLOYEE role | 100 incidents | Violates RBAC intent | New API requires a resolver role |
| Q5 | `reopened_count > 0` | 99 of 150 | Implausibly high reopen rate (66%) | Reported as-is; reopen events are now recorded in `incident_events` |
| Q6 | Service requests with status FULFILLED but no `fulfilled_at` | 8 | Lead-time metrics are missing | Excluded from lead-time averages; flagged |
| Q7 | IMPLEMENTED/FAILED changes with no `actual_start` | 4 | Change success analysis is incomplete | Flagged |
| Q8 | Notifications with status SENT and no `sent_at` | 3 | Inconsistent delivery state | Flagged |
| Q9 | Inactive (ON_LEAVE) requesters with open incidents | 2 users | Follow-up risk | Shown in the backlog report |
| Q10 | Duplicate first+last name pairs | 10 pairs | Ambiguous user picking | UI always shows the employee number and email |
| Q11 | Users in more than one team | 3 | Allowed; noted for workload maths | Supported |
| Q12 | Service ownership and category look round-robin (Printing → Cloud & Platform, HR System → Security Ops, VPN → Database Ops) | 10 services | Wrong routing | Kept as seed data; owning team is editable by admin |
| Q13 | `approvals` table empty | 0 rows | No approval history | Approval workflow designed in the target schema (see domain model) |
| Q14 | Calendar-time SLA breach (response) P1 14/15, P2 29/31, P3 35/72, P4 9/32 | n/a | Seed timestamps ignore SLA targets | Business-hours recalculation in the SLA report |
| Q15 | Every incident has an `sla_id` that matches its priority, and `due_at` equals created + resolution target in calendar time, even though policies say `business_hours_only = TRUE` | 150 | Stored due dates contradict the policy | The new SLA engine recalculates due dates for new and updated tickets; legacy values are kept |

Checks with no issues found: resolved before created, response before created, closed before resolved, open with `resolved_at`, CSAT on open tickets, ASSIGNED asset with no user, warranty before purchase, KB helpful count above views.

## 4. Modelling limitations (DD §"Deliberate modelling limitations") and target-schema fix
| Limitation | Fix in the esm-hub target model (owning service) |
|---|---|
| `approvals.change_id` has no FK | Approvals are split by owner: request-service `request_approvals` and change-service `change_approvals`, each with a real FK |
| Approvals not populated | request-service `approval_steps` config plus generated approval rows; change-service approval policy by type and risk |
| Only the current asset assignee is stored | asset-service `asset_assignments` history table (seeded from the current state) |
| SLA lacks calendars, pause, escalation, versioning | incident-service: calendars, hours, holidays, `pauses_sla` status flag, versioned SLA policies, escalation rules, `incident_events` |
| No status workflow constraint | incident-service `status_transitions` table enforced by the service layer |
| No attachments, watchers, relationships, subcategories, custom fields | `service_categories.parent_id` (subcategories); the rest is deferred (see the delivery report) |
| No business-hours or holiday model | Calendars per office (above) |
| No outbox | Every service has `outbox_events`; a relay publishes to Kafka after commit (transactional outbox) |
| Generic audit payloads | Services publish structured audit events (actor, entity, changed fields, correlation ID, company) to Kafka; audit-service stores them append-only |
