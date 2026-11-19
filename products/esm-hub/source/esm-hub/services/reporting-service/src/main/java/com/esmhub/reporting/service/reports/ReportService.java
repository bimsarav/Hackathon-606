package com.esmhub.reporting.service.reports;

import com.esmhub.common.audit.AuditPublisher;
import com.esmhub.common.security.CurrentUser;
import com.esmhub.common.security.Role;
import com.esmhub.common.web.BusinessRuleException;
import com.esmhub.common.web.CsvWriter;
import com.esmhub.common.web.NotFoundException;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * FR-13 reports over the read model. All figures are computed in SQL and scoped to the caller's company.
 * Definitions follow the previous Python product: reopen rate and SLA percentages use resolved (or responded)
 * incidents as the denominator, so every percentage stays within 0..100.
 */
@Service
public class ReportService {
    static final Set<String> VOLUME_DIMENSIONS = Set.of("month", "week", "priority", "channel", "team", "service", "office", "status");
    static final Set<String> EXPORTS = Set.of("sla-compliance", "workload", "backlog-ageing", "assets", "requests", "changes",
            "incident-volume", "problems");
    private static final String OPEN_REQUEST_STATUSES = "'SUBMITTED','PENDING_APPROVAL','APPROVED','IN_PROGRESS'";

    private final NamedParameterJdbcTemplate jdbc;
    private final AuditPublisher audit;

    public ReportService(NamedParameterJdbcTemplate jdbc, AuditPublisher audit) {
        this.jdbc = jdbc;
        this.audit = audit;
    }

    private static void authorise(CurrentUser me) {
        me.require(Role.TEAM_LEAD, Role.SERVICE_MANAGER, Role.AUDITOR, Role.ADMIN, Role.SERVICE_DESK_AGENT,
                Role.CHANGE_MANAGER, Role.ASSET_MANAGER);
    }

    private static MapSqlParameterSource params(CurrentUser me, ReportRange r) {
        MapSqlParameterSource p = new MapSqlParameterSource("c", me.companyId());
        if (r != null) p.addValue("s", r.from()).addValue("u", r.to());
        return p;
    }

    private List<Map<String, Object>> rows(String sql, MapSqlParameterSource p) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> row : jdbc.queryForList(sql, p)) out.add(new LinkedHashMap<>(row));
        return out;
    }

    private static ReportRange range(LocalDate since, LocalDate until) {
        ReportRange r = ReportRange.of(since, until, LocalDate.now(ZoneOffset.UTC));
        if (r.since().isAfter(r.until())) throw new BusinessRuleException("since must not be after until.");
        return r;
    }

    private static final String PCT = "round(100.0 * count(*) FILTER (WHERE %s) / nullif(%s, 0), 1)";

    @Transactional(readOnly = true)
    public Map<String, Object> summary(CurrentUser me, LocalDate since, LocalDate until) {
        authorise(me);
        ReportRange r = range(since, until);
        MapSqlParameterSource p = params(me, r);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("since", r.since());
        out.put("until", r.until());
        out.putAll(jdbc.queryForMap("SELECT count(*) AS \"created\", count(resolved_at) AS \"resolved\", "
                + PCT.formatted("NOT resolution_breached AND resolved_at IS NOT NULL", "count(resolved_at)") + " AS \"resolutionSlaPct\", "
                + PCT.formatted("NOT response_breached AND first_response_at IS NOT NULL", "count(first_response_at)") + " AS \"responseSlaPct\", "
                + PCT.formatted("reopened_count > 0 AND resolved_at IS NOT NULL", "count(resolved_at)") + " AS \"reopenRatePct\", "
                + "round(avg(satisfaction_score)::numeric, 2) AS \"avgCsat\", "
                + "round(avg(extract(epoch FROM resolved_at - created_at) / 3600)::numeric, 1) AS \"avgResolutionHours\" "
                + "FROM rpt_incidents WHERE company_id = :c AND created_at >= :s AND created_at < :u", p));
        out.putAll(jdbc.queryForMap("SELECT count(*) AS \"openBacklog\", count(*) FILTER (WHERE assigned_user_id IS NULL) AS \"unassigned\", "
                + "count(*) FILTER (WHERE resolution_breached) AS \"openBreached\" FROM rpt_incidents WHERE company_id = :c AND NOT closed", p));
        out.putAll(jdbc.queryForMap("SELECT count(*) FILTER (WHERE status IN (" + OPEN_REQUEST_STATUSES + ")) AS \"openRequests\", "
                + "coalesce(sum(estimated_cost) FILTER (WHERE requested_at >= :s), 0) AS \"requestCost\" "
                + "FROM rpt_requests WHERE company_id = :c", p));
        return out;
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> incidentVolume(CurrentUser me, String by, LocalDate since, LocalDate until) {
        authorise(me);
        String dim = by == null ? "month" : by;
        if (!VOLUME_DIMENSIONS.contains(dim)) throw new BusinessRuleException("by must be one of " + VOLUME_DIMENSIONS + ".");
        String expr = switch (dim) {
            case "month" -> "to_char(date_trunc('month', i.created_at AT TIME ZONE 'UTC'), 'YYYY-MM')";
            case "week" -> "to_char(date_trunc('week', i.created_at AT TIME ZONE 'UTC'), 'IYYY-\"W\"IW')";
            case "priority" -> "coalesce(i.priority, 'Unknown')";
            case "channel" -> "coalesce(i.channel, 'Unknown')";
            case "team" -> "coalesce(t.name, 'Unassigned')";
            case "service" -> "coalesce(s.name, 'None')";
            case "office" -> "coalesce(o.name, 'Unknown')";
            default -> "coalesce(i.status, 'Unknown')";
        };
        return rows("SELECT " + expr + " AS \"key\", count(*) AS \"count\", count(*) FILTER (WHERE i.resolution_breached) AS \"breached\" "
                + "FROM rpt_incidents i LEFT JOIN dir_teams t ON t.team_id = i.assigned_team_id "
                + "LEFT JOIN dir_services s ON s.service_id = i.service_id "
                + "LEFT JOIN dir_users u ON u.user_id = i.requester_id LEFT JOIN dir_offices o ON o.office_id = u.office_id "
                + "WHERE i.company_id = :c AND i.created_at >= :s AND i.created_at < :u GROUP BY 1 ORDER BY 1", params(me, range(since, until)));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> slaCompliance(CurrentUser me, LocalDate since, LocalDate until) {
        authorise(me);
        return rows("SELECT coalesce(priority, 'Unknown') AS \"priority\", count(*) AS \"incidents\", count(first_response_at) AS \"responded\", "
                + PCT.formatted("NOT response_breached AND first_response_at IS NOT NULL", "count(first_response_at)") + " AS \"responseMetPct\", "
                + "count(resolved_at) AS \"resolved\", "
                + PCT.formatted("NOT resolution_breached AND resolved_at IS NOT NULL", "count(resolved_at)") + " AS \"resolutionMetPct\", "
                + "round(avg(extract(epoch FROM first_response_at - created_at) / 60)::numeric, 0) AS \"avgResponseMin\", "
                + "round(avg(extract(epoch FROM resolved_at - created_at) / 60)::numeric, 0) AS \"avgResolutionMin\" "
                + "FROM rpt_incidents WHERE company_id = :c AND created_at >= :s AND created_at < :u GROUP BY 1 ORDER BY 1",
                params(me, range(since, until)));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> backlogAgeing(CurrentUser me) {
        authorise(me);
        return rows("SELECT bucket AS \"bucket\", priority AS \"priority\", count(*) AS \"count\" FROM ("
                + "SELECT coalesce(priority, 'Unknown') AS priority, "
                + "CASE WHEN age < 1 THEN '0-1d' WHEN age < 3 THEN '1-3d' WHEN age < 7 THEN '3-7d' WHEN age < 30 THEN '7-30d' ELSE '30d+' END AS bucket, "
                + "CASE WHEN age < 1 THEN 1 WHEN age < 3 THEN 2 WHEN age < 7 THEN 3 WHEN age < 30 THEN 4 ELSE 5 END AS ord "
                + "FROM (SELECT priority, extract(epoch FROM now() - created_at) / 86400 AS age FROM rpt_incidents "
                + "WHERE company_id = :c AND NOT closed) a) x GROUP BY bucket, ord, priority ORDER BY ord, priority", params(me, null));
    }

    /** Open tickets per team and assignee with the effort logged on those tickets (snapshots carry total minutes per incident). */
    @Transactional(readOnly = true)
    public List<Map<String, Object>> workload(CurrentUser me) {
        authorise(me);
        return rows("SELECT coalesce(t.name, 'Unassigned') AS \"team\", coalesce(u.first_name || ' ' || u.last_name, 'Unassigned') AS \"assignee\", "
                + "count(*) AS \"open\", count(*) FILTER (WHERE i.resolution_breached) AS \"breached\", "
                + "count(*) FILTER (WHERE i.priority IN ('P1', 'P2')) AS \"p1P2\", coalesce(sum(i.worklog_minutes), 0) AS \"effortMinutes\" "
                + "FROM rpt_incidents i LEFT JOIN dir_teams t ON t.team_id = i.assigned_team_id "
                + "LEFT JOIN dir_users u ON u.user_id = i.assigned_user_id "
                + "WHERE i.company_id = :c AND NOT i.closed GROUP BY t.name, u.first_name, u.last_name "
                + "ORDER BY count(*) DESC, 1, 2", params(me, null));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> assets(CurrentUser me) {
        authorise(me);
        return rows("SELECT asset_type AS \"assetType\", status AS \"status\", warranty AS \"warranty\", count(*) AS \"count\", "
                + "coalesce(sum(purchase_cost), 0) AS \"value\" FROM (SELECT asset_type, status, purchase_cost, "
                + "CASE WHEN warranty_end IS NULL THEN 'UNKNOWN' WHEN warranty_end < current_date THEN 'EXPIRED' "
                + "WHEN warranty_end <= current_date + 90 THEN 'EXPIRING' ELSE 'ACTIVE' END AS warranty "
                + "FROM rpt_assets WHERE company_id = :c) a GROUP BY asset_type, status, warranty ORDER BY asset_type, status, warranty",
                params(me, null));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> requests(CurrentUser me, LocalDate since, LocalDate until) {
        authorise(me);
        return rows("SELECT coalesce(s.name, 'None') AS \"service\", count(*) AS \"requests\", "
                + "count(*) FILTER (WHERE r.status = 'FULFILLED') AS \"fulfilled\", count(*) FILTER (WHERE r.status = 'REJECTED') AS \"rejected\", "
                + "coalesce(sum(r.estimated_cost), 0) AS \"totalCost\", "
                + "round(avg(extract(epoch FROM r.fulfilled_at - r.requested_at) / 3600)::numeric, 1) AS \"avgFulfilmentHours\", "
                + "round(avg(extract(epoch FROM r.approved_at - r.requested_at) / 3600)::numeric, 1) AS \"avgApprovalHours\" "
                + "FROM rpt_requests r LEFT JOIN dir_services s ON s.service_id = r.service_id "
                + "WHERE r.company_id = :c AND r.requested_at >= :s AND r.requested_at < :u GROUP BY s.name "
                + "ORDER BY coalesce(sum(r.estimated_cost), 0) DESC, 1", params(me, range(since, until)));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> changes(CurrentUser me) {
        authorise(me);
        return rows("SELECT change_type AS \"changeType\", coalesce(risk_level, 'UNASSESSED') AS \"risk\", count(*) AS \"changes\", "
                + "count(*) FILTER (WHERE status IN ('IMPLEMENTED', 'CLOSED')) AS \"successful\", "
                + "count(*) FILTER (WHERE status = 'FAILED') AS \"failed\", "
                + PCT.formatted("status = 'FAILED'", "count(*) FILTER (WHERE status IN ('IMPLEMENTED', 'CLOSED', 'FAILED'))") + " AS \"failureRatePct\" "
                + "FROM rpt_changes WHERE company_id = :c GROUP BY 1, 2 ORDER BY 1, 2", params(me, null));
    }

    /** Problem-record coverage: share of incidents linked to a problem, problems by status, top recurring services. */
    @Transactional(readOnly = true)
    public Map<String, Object> problems(CurrentUser me) {
        authorise(me);
        MapSqlParameterSource p = params(me, null);
        Map<String, Object> coverage = new LinkedHashMap<>(jdbc.queryForMap(
                "SELECT count(*) AS \"incidents\", count(*) FILTER (WHERE EXISTS (SELECT 1 FROM rpt_problem_incidents l "
                        + "JOIN rpt_problems pr ON pr.problem_id = l.problem_id WHERE l.incident_id = i.incident_id "
                        + "AND pr.company_id = i.company_id)) AS \"linked\" FROM rpt_incidents i WHERE i.company_id = :c", p));
        long total = ((Number) coverage.get("incidents")).longValue();
        long linked = ((Number) coverage.get("linked")).longValue();
        coverage.put("coveragePct", total == 0 ? null : Math.round(1000.0 * linked / total) / 10.0);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("coverage", coverage);
        out.put("byStatus", problemsByStatus(p));
        out.put("topServices90d", rows("SELECT coalesce(s.name, 'None') AS \"service\", count(*) AS \"incidents90d\" FROM rpt_incidents i "
                + "LEFT JOIN dir_services s ON s.service_id = i.service_id WHERE i.company_id = :c AND i.created_at >= now() - interval '90 days' "
                + "GROUP BY s.name ORDER BY count(*) DESC, 1 LIMIT 5", p));
        return out;
    }

    private List<Map<String, Object>> problemsByStatus(MapSqlParameterSource p) {
        return rows("SELECT status AS \"status\", count(*) AS \"count\", count(*) FILTER (WHERE known_error) AS \"knownErrors\" "
                + "FROM rpt_problems WHERE company_id = :c GROUP BY status ORDER BY status", p);
    }

    /** CSV of one report (incident-volume uses the {@code by} dimension). The export is audited. */
    @Transactional
    public ResponseEntity<byte[]> export(CurrentUser me, String name, String by, LocalDate since, LocalDate until) {
        authorise(me);
        if (!EXPORTS.contains(name)) throw new NotFoundException("Unknown report.");
        List<Map<String, Object>> data = switch (name) {
            case "sla-compliance" -> slaCompliance(me, since, until);
            case "workload" -> workload(me);
            case "backlog-ageing" -> backlogAgeing(me);
            case "assets" -> assets(me);
            case "requests" -> requests(me, since, until);
            case "changes" -> changes(me);
            case "incident-volume" -> incidentVolume(me, by, since, until);
            default -> problemsByStatus(params(me, null));
        };
        audit.record("REPORT", name, "EXPORT", null, Map.of("report", name, "rows", data.size()));
        List<String> header = data.isEmpty() ? List.of("no_data") : new ArrayList<>(data.get(0).keySet());
        List<List<?>> body = new ArrayList<>();
        for (Map<String, Object> row : data) body.add(header.stream().map(row::get).toList());
        return CsvWriter.response(name + ".csv", header, body);
    }
}
