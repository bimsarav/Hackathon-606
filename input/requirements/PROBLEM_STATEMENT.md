# Enterprise Service Management Platform (ESMP) — Problem Statement

## 1. Organisation
Northstar Holdings is a fictional multi-office enterprise with locations in Abu Dhabi, Dubai, London and Colombo. It has departments including IT, Finance, HR, Operations, Sales and Customer Support.

## 2. Current situation
Employees report technology incidents through email, phone and chat. Requests are tracked in spreadsheets. Support teams use separate tools for assets, approvals and knowledge articles. Management cannot reliably measure service quality, SLA performance, workload or recurring problems.

## 3. Business goal
Build a secure, multi-office Enterprise Service Management Platform that centralises service delivery, automates operational workflows and provides trustworthy management analytics.

## 4. Users and personas
- Employee: creates and tracks incidents and service requests, searches knowledge articles.
- Service desk agent: triages, categorises, prioritises and assigns tickets.
- Resolver/technician: investigates, records work, communicates and resolves.
- Team lead: manages queues, workload, escalations and team performance.
- Service manager: configures services, SLAs, service catalogue and reports.
- Change manager: assesses and approves changes and tracks implementation.
- Asset manager: manages inventory, assignments, warranty and lifecycle.
- Auditor: reads audit trails and compliance evidence.
- Platform administrator: manages configuration, access and integrations.

## 5. Functional requirements
1. Authentication, user profile and role-based access control.
2. Multi-company, office and department hierarchy.
3. Incident lifecycle: create, classify, prioritise, assign, comment, worklog, resolve, close and reopen.
4. Service request catalogue with configurable approval steps.
5. SLA policies with response/resolution clocks, business-hour calendars, pause conditions and escalation.
6. Team queues, workload views and assignment rules.
7. Problem management linking incidents to root-cause investigations and known errors.
8. Change management with risk, impact, approvals, schedule, implementation and rollback.
9. Asset inventory, assignment history, warranty and lifecycle status.
10. Knowledge base with publishing workflow, search and usefulness feedback.
11. Notifications with delivery status and retry handling.
12. Audit trail for security-sensitive and business-critical changes.
13. Dashboards and reports for SLA compliance, ticket volumes, ageing, reopen rate, backlog, workload, asset estate and request costs.
14. Search, filtering, pagination and export for authorised users.
15. Administrative configuration for priorities, statuses, categories, services, teams and SLA policies.

## 6. Non-functional requirements
- Secure by default; least-privilege access and tenant/company data boundaries.
- Responsive web UI and documented REST API.
- Relational data integrity and migration-based schema evolution.
- Structured application logs with correlation IDs; do not log secrets or sensitive ticket contents unnecessarily.
- Health/readiness endpoints, metrics and centralised error handling.
- Automated unit, integration, API-contract and end-to-end tests.
- Containerised local deployment and documented production deployment path.
- Backup, restore, retention and disaster-recovery procedures.
- Accessibility and usable keyboard navigation.
- Configurable timezone and business calendars; store timestamps consistently.
- Idempotent operations for retryable integrations and notifications.

## 7. Important business rules to clarify
- SLA clock: calendar time or business hours? Which holidays and timezones apply?
- When should SLA pause (waiting for requester, vendor, approval)?
- Who can change priority, requester, assignee and resolution?
- Can a closed ticket be reopened, and within what period?
- Are approvals sequential, parallel or conditional by cost/service?
- What are the data retention and deletion requirements?
- Are offices separate legal entities or only locations?
- Which notification channels are mandatory?
- What are the required integrations and identity provider?
- What are the target availability, recovery time and recovery point objectives?

Do not invent answers. Ask the product owner for decisions and record approved answers.

## 8. Seed data caveats
The supplied SQL dump is synthetic training data, not a complete production dataset. It intentionally includes varied statuses, priorities, channels, teams, services, timestamps, comments, worklogs, assets, requests, changes and problems. Some records are deliberately imperfect or incomplete so the team can perform data profiling and identify modelling gaps.

## 9. Expected deliverables
- Domain model, ERD and data dictionary.
- Data profiling and quality report.
- Functional and non-functional requirements catalogue.
- User stories with acceptance criteria.
- Architecture decision records and deployment architecture.
- API specification and database migration strategy.
- Working application source code.
- Automated tests and test evidence.
- Security threat model and security test report.
- Docker-based local environment and deployment documentation.
- Dashboards and sample operational reports.
- Runbooks, backup/restore and monitoring guidance.
- Final traceability matrix mapping requirements to implementation and tests.

## 10. Initial assignment
Analyse the problem statement and SQL dump before writing application code. Identify schema limitations, missing relationships, data quality issues, workflow gaps, security concerns and reporting opportunities. Produce questions where business decisions are missing. Do not assume the existing schema is necessarily the final target design.
