package com.esmhub.audit.service.audit;

import com.esmhub.audit.service.audit.AuditDtos.AuditFilter;
import com.esmhub.audit.service.audit.AuditDtos.AuditView;
import com.esmhub.common.audit.AuditPublisher.AuditPayload;
import com.esmhub.common.events.EventEnvelope;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Append-only access to audit_records (insert and select only; the DB trigger rejects anything else). */
@Repository
public class AuditStore {
    private static final String COLS = "audit_id, service, actor_user_id, entity_type, entity_id, action, old_values::text AS old_values, "
            + "new_values::text AS new_values, source_ip, correlation_id, occurred_at";

    private final JdbcClient jdbc;
    private final JsonMapper mapper;

    public AuditStore(JdbcClient jdbc, JsonMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    public void append(EventEnvelope env, AuditPayload p) {
        jdbc.sql("INSERT INTO audit_records (event_id, company_id, service, actor_user_id, entity_type, entity_id, action, "
                        + "old_values, new_values, source_ip, correlation_id, occurred_at) "
                        + "VALUES (:eventId, :company, :service, :actor, :entityType, :entityId, :action, "
                        + "CAST(:oldV AS jsonb), CAST(:newV AS jsonb), :ip, :corr, :at) ON CONFLICT (event_id) DO NOTHING")
                .param("eventId", env.eventId()).param("company", env.companyId())
                .param("service", p.service() == null ? "unknown" : p.service())
                .param("actor", env.actorId()).param("entityType", p.entityType()).param("entityId", p.entityId())
                .param("action", p.action())
                .param("oldV", p.oldValues() == null ? null : mapper.writeValueAsString(p.oldValues()))
                .param("newV", p.newValues() == null ? null : mapper.writeValueAsString(p.newValues()))
                .param("ip", p.sourceIp()).param("corr", env.correlationId())
                .param("at", Timestamp.from(env.occurredAt() == null ? Instant.now() : env.occurredAt()))
                .update();
    }

    private static String where(AuditFilter f) {
        StringBuilder w = new StringBuilder(" WHERE company_id = :company");
        if (f.service() != null) w.append(" AND service = :service");
        if (f.entityType() != null) w.append(" AND entity_type = :entityType");
        if (f.entityId() != null) w.append(" AND entity_id = :entityId");
        if (f.action() != null) w.append(" AND action = :action");
        if (f.actorId() != null) w.append(" AND actor_user_id = :actor");
        if (f.from() != null) w.append(" AND occurred_at >= :from");
        if (f.to() != null) w.append(" AND occurred_at <= :to");
        return w.toString();
    }

    private JdbcClient.StatementSpec bind(String sql, long company, AuditFilter f) {
        var s = jdbc.sql(sql).param("company", company);
        if (f.service() != null) s = s.param("service", f.service());
        if (f.entityType() != null) s = s.param("entityType", f.entityType());
        if (f.entityId() != null) s = s.param("entityId", f.entityId());
        if (f.action() != null) s = s.param("action", f.action());
        if (f.actorId() != null) s = s.param("actor", f.actorId());
        if (f.from() != null) s = s.param("from", Timestamp.from(f.from()));
        if (f.to() != null) s = s.param("to", Timestamp.from(f.to()));
        return s;
    }

    public long count(long company, AuditFilter f) {
        return bind("SELECT count(*) FROM audit_records" + where(f), company, f).query(Long.class).single();
    }

    public List<AuditView> find(long company, AuditFilter f, int limit, long offset) {
        return bind("SELECT " + COLS + " FROM audit_records" + where(f)
                + " ORDER BY occurred_at DESC, audit_id DESC LIMIT " + limit + " OFFSET " + offset, company, f)
                .query((rs, n) -> new AuditView(rs.getLong("audit_id"), rs.getString("service"),
                        (Long) rs.getObject("actor_user_id"), rs.getString("entity_type"), rs.getString("entity_id"),
                        rs.getString("action"), json(rs.getString("old_values")), json(rs.getString("new_values")),
                        rs.getString("source_ip"), rs.getString("correlation_id"), rs.getTimestamp("occurred_at").toInstant()))
                .list();
    }

    private JsonNode json(String s) { return s == null ? null : mapper.readTree(s); }
}
