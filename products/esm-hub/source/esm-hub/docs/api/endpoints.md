# API Endpoint Index (via the gateway, base `/api/v1`)

Detailed request and response schemas are in each service's OpenAPI document (`/v3/api-docs` on the service, or `docs/api/<service>.json`). Errors are problem+json `{title, status, detail, requestId, errors?}`. Lists return `{items, total, page, size}` and take `?page=1&size=25` (max 200).

| Service | Endpoints |
|---|---|
| directory | `POST /auth/login` (public) · `GET /auth/me` · `POST /auth/password` · `GET /users?q&includeInactive` · `GET /users/{id}` · `POST /admin/users` · `PATCH /admin/users/{id}` · `POST /admin/users/{id}/password` · `GET /reference` (offices, departments, teams, categories, services, roles) · `GET /teams/{id}/members` · `POST,PUT /admin/offices[/{id}]` · `POST /admin/departments` · `POST,PUT /admin/teams[/{id}]` · `POST /admin/categories` · `POST,PUT /admin/services[/{id}]` · `GET /.well-known/jwks.json` (service only) |
| incident | `GET,POST /incidents` (view=mine/assigned/queue/open/unassigned/all, status, priority, team, assignee, q, breached, sort; `Idempotency-Key`) · `GET /incidents/export` · `GET /incidents/meta/priorities` · `GET,PATCH /incidents/{id}` · `POST /incidents/{id}/assign` · `/status` · `/reopen` · `/comments` · `/worklogs` · `/satisfaction` · `GET,POST /problems` · `GET,PATCH /problems/{id}` · `POST /problems/{id}/incidents` · `DELETE /problems/{id}/incidents/{incidentId}` · `PUT /admin/priorities/{id}` · `GET,POST /admin/sla-policies` · `GET,POST /admin/calendars` · `PUT /admin/calendars/{id}` · `GET,POST /admin/assignment-rules` · `PUT /admin/assignment-rules/{id}` · `GET,POST /admin/escalation-rules` |
| request | `GET,POST /catalogue` · `PUT /catalogue/{id}` · `GET,POST /requests` (`Idempotency-Key`) · `GET /requests/{id}` · `POST /requests/{id}/status` · `GET /approvals` · `POST /approvals/{id}/decision` |
| change | `GET,POST /changes` (view, status, type, risk, q) · `GET,PUT /changes/{id}` · `POST /changes/{id}/status` · `GET /changes-calendar?from&to` · `GET /change-approvals` · `POST /change-approvals/{id}/decision` |
| asset | `GET,POST /assets` · `GET /assets/export` · `GET,PATCH /assets/{id}` (includes history) · `POST /assets/{id}/assign` · `POST /assets/{id}/status` |
| knowledge | `GET,POST /kb/articles` (`q` = full-text) · `GET,PATCH /kb/articles/{id}` · `POST /kb/articles/{id}/status` · `POST /kb/articles/{id}/feedback` |
| notification | `GET /notifications?unread` · `GET /notifications/unread-count` · `POST /notifications/{id}/read` · `POST /notifications/read-all` · `GET /admin/notifications?status` · `POST /admin/notifications/{id}/retry` |
| audit | `GET /audit` (service, entityType, entityId, action, actorId, from, to) · `GET /audit/export` |
| reporting | `GET /reports/summary` · `/incident-volume?by=month,week,priority,channel,team,service,office,status` · `/sla-compliance` · `/backlog-ageing` · `/workload` · `/assets` · `/requests` · `/changes` · `/problems` · `/{name}/export` (`since`, `until` = yyyy-MM-dd) |

Approvals inbox in the UI: merge `GET /approvals` (requests) and `GET /change-approvals` (changes).
