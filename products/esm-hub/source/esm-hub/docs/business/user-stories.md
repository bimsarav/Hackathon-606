# Epics, User Stories and Acceptance Criteria

Format: **US-x** As a <persona>, I want <capability> so that <value>. AC = acceptance criteria; the tests that prove them are named in `documentation/traceability-matrix.md`.

## E1 Access and organisation (FR-1, FR-2, FR-15)
- **US-1** As any user, I want to sign in with my company account so that I can use the platform securely.
  AC: valid credentials return a token; wrong password or unknown email gives the same 401; 5 failures lock the account for 15 minutes; deactivated users are rejected immediately.
- **US-2** As an admin, I want to create users and manage their roles and teams so that access follows least privilege.
  AC: duplicate emails are rejected (409); unknown roles are rejected (422); role changes are audited as ROLE_CHANGE; an admin cannot remove their own ADMIN role.
- **US-3** As an admin, I want to maintain offices, departments and teams so that routing and reporting reflect the organisation.
  AC: an office needs a valid IANA timezone and is linked to the matching calendar automatically.

## E2 Incident management (FR-3, FR-5, FR-6)
- **US-4** As an employee, I want to report an incident in the portal and track it so that I don't need email or phone.
  AC: the ticket gets an INC number; it is routed to a team by assignment rule; I see only my own tickets; I am notified about progress.
- **US-5** As a service desk agent, I want to triage (prioritise, classify, assign) so that work reaches the right resolver.
  AC: only desk roles change priority; the assignee must belong to the team and hold a resolver role; priority changes recalculate SLA due times.
- **US-6** As a technician, I want to comment (public or internal), log work and move the ticket through its workflow so that progress is recorded.
  AC: invalid transitions return 422; RESOLVED needs a resolution code; requesters never see internal notes or worklogs.
- **US-7** As a requester, I want to reopen a resolved incident within 7 days, and to rate it, so that unresolved issues aren't lost.
  AC: reopening after 7 days or after close is refused; the reopen count increments and the team is notified.
- **US-8** As a team lead, I want SLA clocks on business hours with pauses and automatic escalation so that breaches are prevented.
  AC: due dates skip nights, weekends and holidays in the requester's office timezone; PENDING_USER pauses the resolution clock; breach and at-risk escalations are sent once per trigger.
- **US-9** As a team lead, I want queue and workload views so that I can balance work.
  AC: views for mine, assigned, team queue, unassigned and open; a workload report by team and assignee.

## E3 Service requests (FR-4)
- **US-10** As an employee, I want to order from a catalogue so that requests are standardised.
- **US-11** As an approver, I want an approvals inbox so that I can approve or reject with a comment.
  AC: steps are sequential; the manager step comes first; cost-based steps apply only above their threshold; self-approval is impossible; a second decision returns 409.
- **US-12** As a fulfilment technician, I want to progress approved requests to fulfilled so that lead times are measured.

## E4 Problem and change (FR-7, FR-8)
- **US-13** As a resolver, I want to group incidents under a problem, record the root cause and publish known errors so that recurring issues are fixed.
  AC: a known error needs a workaround; resolving needs a root cause; linked problems are shown on the incident.
- **US-14** As a change manager, I want risk and impact assessment, approvals, scheduling and implementation tracking so that changes are controlled.
  AC: assessment requires risk, impact, window and rollback plan; STANDARD is pre-approved; HIGH-risk NORMAL needs two approvals; the plan is locked after approval; only change managers close.

## E5 Assets and knowledge (FR-9, FR-10)
- **US-15** As an asset manager, I want an inventory with assignment history, warranty state and lifecycle so that the estate is controlled.
- **US-16** As an employee, I want to search the knowledge base and rate articles so that I can help myself.
  AC: full-text ranked search; drafts are invisible to others; four-eyes publishing; one vote per user.

## E6 Notifications, audit and reporting (FR-11 to FR-14)
- **US-17** As a user, I want in-app and email notifications so that I don't miss updates.
  AC: email is delivered via the outbox with retries and backoff and dead-lettered after 6 attempts; admins can retry; no duplicates.
- **US-18** As an auditor, I want an immutable, filterable and exportable audit trail.
- **US-19** As a service manager, I want dashboards (SLA compliance, volume, ageing, reopen rate, backlog, workload, assets, request costs, changes, problems) with CSV export.

## Milestones
| Milestone | Content |
|---|---|
| M1 | Discovery, data profiling, architecture, Gradle foundation |
| M2 | directory-service, incident-service (with SLA) |
| M3 | request, change, asset, knowledge services |
| M4 | notification, audit, reporting over Kafka |
| M5 | React web UI and gateway |
| M6 | Docker deployment, CI, Playwright E2E, runbooks, delivery |
