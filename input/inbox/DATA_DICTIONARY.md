# Data Dictionary and Analysis Guide

Schema: `esmp`

| Table | Purpose |
|---|---|
| companies, offices, departments | Organisation hierarchy |
| users, roles, user_roles | Identity and authorisation seed model |
| teams, team_members | Resolver groups and membership |
| service_categories, services | Service catalogue |
| priorities, ticket_statuses, sla_policies | Ticket and SLA reference data |
| assets | Hardware/software inventory and current assignment |
| incidents | Main incident records and lifecycle timestamps |
| incident_comments, worklogs | Collaboration and effort tracking |
| service_requests, approvals | Catalogue requests and approvals |
| problems, incident_problem_links | Root-cause management |
| change_requests | Planned and emergency changes |
| knowledge_articles | Self-service knowledge |
| notifications | Outbound notification history |
| audit_logs | Change/audit evidence |

## Suggested profiling questions
1. Incident volume by month, office, service, priority, channel and team.
2. Response and resolution duration by priority; compare against SLA targets.
3. SLA breach rate. Note: the seed has simplified SLA fields; business-hours calendars and pause events are not modelled.
4. Open backlog ageing and assignment gaps.
5. Reopened incidents and satisfaction scores.
6. Work effort by team, service and incident priority.
7. Repeated incident patterns and problem-record coverage.
8. Asset assignment coverage, warranty expiry and lifecycle distribution.
9. Request approval and fulfilment lead times.
10. Change success/failure rate and risk distribution.
11. Notification delivery failure rate.
12. Referential integrity, duplicate values, missing timestamps and inconsistent states.

## Deliberate modelling limitations to discover
- `approvals.change_id` is not declared as a foreign key to `change_requests`.
- Approval rows in the seed are not populated; design realistic approval workflows.
- Asset assignment stores only the current assignee; no historical assignment table exists.
- SLA policy model lacks calendars, pause intervals, escalation rules and version history.
- Incident status transitions are not constrained by a workflow table.
- Incident priority and SLA policy values are seeded but must be validated against service-specific policy rules.
- No attachment, watcher, relationship, category/subcategory or custom-field tables.
- No explicit business-hours calendar or public-holiday model.
- No outbox/event table for reliable notification/integration delivery.
- `audit_logs` seed payloads are intentionally generic and do not represent a complete audit design.
