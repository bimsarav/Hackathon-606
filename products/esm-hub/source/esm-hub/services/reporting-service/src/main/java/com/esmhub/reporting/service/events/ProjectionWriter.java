package com.esmhub.reporting.service.events;

import com.esmhub.common.contracts.DomainContracts.*;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/** Idempotent upserts and deletes (tombstones) of the read-model tables. */
@Component
public class ProjectionWriter {
    private final JdbcTemplate jdbc;

    public ProjectionWriter(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    static OffsetDateTime ts(Instant i) { return i == null ? null : OffsetDateTime.ofInstant(i, ZoneOffset.UTC); }

    public void upsert(IncidentSnapshot s) {
        jdbc.update("""
                INSERT INTO rpt_incidents (incident_id, company_id, ticket_no, title, status, closed, priority, service_id, channel,
                  requester_id, assigned_team_id, assigned_user_id, created_at, first_response_at, resolved_at, closed_at,
                  response_due_at, due_at, response_breached, resolution_breached, sla_paused, reopened_count,
                  satisfaction_score, worklog_minutes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (incident_id) DO UPDATE SET company_id = EXCLUDED.company_id, ticket_no = EXCLUDED.ticket_no,
                  title = EXCLUDED.title, status = EXCLUDED.status, closed = EXCLUDED.closed, priority = EXCLUDED.priority,
                  service_id = EXCLUDED.service_id, channel = EXCLUDED.channel, requester_id = EXCLUDED.requester_id,
                  assigned_team_id = EXCLUDED.assigned_team_id, assigned_user_id = EXCLUDED.assigned_user_id,
                  created_at = EXCLUDED.created_at, first_response_at = EXCLUDED.first_response_at,
                  resolved_at = EXCLUDED.resolved_at, closed_at = EXCLUDED.closed_at,
                  response_due_at = EXCLUDED.response_due_at, due_at = EXCLUDED.due_at,
                  response_breached = EXCLUDED.response_breached, resolution_breached = EXCLUDED.resolution_breached,
                  sla_paused = EXCLUDED.sla_paused, reopened_count = EXCLUDED.reopened_count,
                  satisfaction_score = EXCLUDED.satisfaction_score, worklog_minutes = EXCLUDED.worklog_minutes""",
                s.incidentId(), s.companyId(), s.ticketNo(), s.title(), s.status(), s.closed(), s.priority(), s.serviceId(),
                s.channel(), s.requesterId(), s.assignedTeamId(), s.assignedUserId(), ts(s.createdAt()),
                ts(s.firstResponseAt()), ts(s.resolvedAt()), ts(s.closedAt()), ts(s.responseDueAt()), ts(s.dueAt()),
                s.responseBreached(), s.resolutionBreached(), s.slaPaused(), s.reopenedCount(), s.satisfactionScore(),
                s.worklogMinutes());
    }

    public void upsert(ProblemSnapshot s) {
        jdbc.update("""
                INSERT INTO rpt_problems (problem_id, company_id, problem_no, title, status, known_error, owner_team_id,
                  created_at, resolved_at) VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT (problem_id) DO UPDATE SET company_id = EXCLUDED.company_id, problem_no = EXCLUDED.problem_no,
                  title = EXCLUDED.title, status = EXCLUDED.status, known_error = EXCLUDED.known_error,
                  owner_team_id = EXCLUDED.owner_team_id, created_at = EXCLUDED.created_at, resolved_at = EXCLUDED.resolved_at""",
                s.problemId(), s.companyId(), s.problemNo(), s.title(), s.status(), s.knownError(), s.ownerTeamId(),
                ts(s.createdAt()), ts(s.resolvedAt()));
        jdbc.update("DELETE FROM rpt_problem_incidents WHERE problem_id = ?", s.problemId());
        List<Long> ids = s.incidentIds() == null ? List.of() : s.incidentIds().stream().distinct().toList();
        for (Long incidentId : ids) {
            jdbc.update("INSERT INTO rpt_problem_incidents (problem_id, incident_id) VALUES (?, ?)", s.problemId(), incidentId);
        }
    }

    public void upsert(RequestSnapshot s) {
        jdbc.update("""
                INSERT INTO rpt_requests (request_id, company_id, request_no, title, status, requester_id, service_id, item_id,
                  estimated_cost, assigned_team_id, requested_at, approved_at, fulfilled_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (request_id) DO UPDATE SET company_id = EXCLUDED.company_id, request_no = EXCLUDED.request_no,
                  title = EXCLUDED.title, status = EXCLUDED.status, requester_id = EXCLUDED.requester_id,
                  service_id = EXCLUDED.service_id, item_id = EXCLUDED.item_id, estimated_cost = EXCLUDED.estimated_cost,
                  assigned_team_id = EXCLUDED.assigned_team_id, requested_at = EXCLUDED.requested_at,
                  approved_at = EXCLUDED.approved_at, fulfilled_at = EXCLUDED.fulfilled_at""",
                s.requestId(), s.companyId(), s.requestNo(), s.title(), s.status(), s.requesterId(), s.serviceId(),
                s.itemId(), s.estimatedCost(), s.assignedTeamId(), ts(s.requestedAt()), ts(s.approvedAt()),
                ts(s.fulfilledAt()));
    }

    public void upsert(ChangeSnapshot s) {
        jdbc.update("""
                INSERT INTO rpt_changes (change_id, company_id, change_no, title, change_type, status, risk_level, impact,
                  owner_team_id, requester_id, planned_start, planned_end, actual_start, actual_end, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (change_id) DO UPDATE SET company_id = EXCLUDED.company_id, change_no = EXCLUDED.change_no,
                  title = EXCLUDED.title, change_type = EXCLUDED.change_type, status = EXCLUDED.status,
                  risk_level = EXCLUDED.risk_level, impact = EXCLUDED.impact, owner_team_id = EXCLUDED.owner_team_id,
                  requester_id = EXCLUDED.requester_id, planned_start = EXCLUDED.planned_start,
                  planned_end = EXCLUDED.planned_end, actual_start = EXCLUDED.actual_start,
                  actual_end = EXCLUDED.actual_end, created_at = EXCLUDED.created_at""",
                s.changeId(), s.companyId(), s.changeNo(), s.title(), s.changeType(), s.status(), s.riskLevel(), s.impact(),
                s.ownerTeamId(), s.requesterId(), ts(s.plannedStart()), ts(s.plannedEnd()), ts(s.actualStart()),
                ts(s.actualEnd()), ts(s.createdAt()));
    }

    public void upsert(AssetSnapshot s) {
        jdbc.update("""
                INSERT INTO rpt_assets (asset_id, company_id, asset_tag, asset_type, status, assigned_user_id, office_id,
                  purchase_date, warranty_end, purchase_cost) VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (asset_id) DO UPDATE SET company_id = EXCLUDED.company_id, asset_tag = EXCLUDED.asset_tag,
                  asset_type = EXCLUDED.asset_type, status = EXCLUDED.status, assigned_user_id = EXCLUDED.assigned_user_id,
                  office_id = EXCLUDED.office_id, purchase_date = EXCLUDED.purchase_date,
                  warranty_end = EXCLUDED.warranty_end, purchase_cost = EXCLUDED.purchase_cost""",
                s.assetId(), s.companyId(), s.assetTag(), s.assetType(), s.status(), s.assignedUserId(), s.officeId(),
                s.purchaseDate(), s.warrantyEnd(), s.purchaseCost());
    }

    /** Tombstone: deletes the row of {@code table} (one of the rpt_* tables) with the given id column value. */
    public void delete(String table, String idColumn, long id) {
        jdbc.update("DELETE FROM " + table + " WHERE " + idColumn + " = ?", id);
    }
}
