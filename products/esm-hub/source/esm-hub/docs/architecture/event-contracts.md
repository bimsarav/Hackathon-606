# Event Contracts

Java source of truth: `libs/esm-common/src/main/java/com/esmhub/common/contracts/` (`DirectoryContracts`, `DomainContracts`). All messages use the `EventEnvelope`; the `payload` is one of these records. Changes must be additive (new nullable fields).

## State topics (compacted, key = aggregate id, event type `<aggregate>.snapshot`)
| Topic | Payload | Producer | Consumers |
|---|---|---|---|
| directory.users / teams / services / offices | `DirectoryContracts.*Snapshot` | directory-service | replicas (esm-directory-replica), reporting |
| incident.incidents | `DomainContracts.IncidentSnapshot` | incident-service | reporting |
| incident.problems | `DomainContracts.ProblemSnapshot` | incident-service | reporting |
| request.requests | `DomainContracts.RequestSnapshot` | request-service | reporting |
| change.changes | `DomainContracts.ChangeSnapshot` | change-service | reporting |
| asset.assets | `DomainContracts.AssetSnapshot` | asset-service | reporting |

Producers publish a snapshot after **every** state change (via the outbox, same transaction) and implement a `SnapshotSource` for the bootstrap.

## Domain-event topics (key = aggregate id, payload `DomainContracts.DomainEvent`)
`DomainEvent{entityType, entityId, reference (e.g. INC-000151), notification: NotificationIntent{notifyUserIds, subject, message, link, email}, facts{...}}`.
The producer computes the recipients (it knows requester, assignee, team lead, approvers). notification-service is generic: it stores one in-app notification per recipient and sends email when `email=true`. It never needs domain knowledge.

| Topic | Event types (minimum) |
|---|---|
| incident.events | incident.created, incident.assigned, incident.status_changed, incident.commented, incident.reopened, incident.sla_escalated |
| request.events | request.submitted, request.approval_requested, request.approved, request.rejected, request.fulfilled |
| change.events | change.approval_requested, change.approved, change.rejected, change.failed |
| asset.events | asset.assigned |
| knowledge.events | article.review_requested, article.published |
| audit.events | `AuditPublisher.AuditPayload` (all services) → audit-service |

`link` is a UI route, e.g. `/incidents/151`, `/requests/46`, `/changes/21`, `/approvals`, `/assets/7`, `/kb/12`.
