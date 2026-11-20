-- audit-service demo seed: the 80 legacy audit logs (all actors belong to company 1).
-- Legacy rows have no originating service or Kafka event: service = 'legacy', event_id NULL, correlation_id NULL.
-- entity_id (bigint) becomes text; source_ip (inet) is kept as text; legacy audit_id values are kept.
SELECT format('INSERT INTO audit_records (audit_id, company_id, service, actor_user_id, entity_type, entity_id, action, old_values, new_values, source_ip, occurred_at, recorded_at) VALUES (%s, 1, ''legacy'', %L, %L, %L, %L, %L::jsonb, %L::jsonb, %L, %L, %L);',
              audit_id, actor_user_id, entity_type, entity_id::text, action, old_values::text, new_values::text,
              host(source_ip), occurred_at, occurred_at)
FROM esmp.audit_logs ORDER BY audit_id;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('audit_records', 'audit_id')) v(t, c);
