-- change-service demo seed: the 20 legacy change requests and the pending approval for changes waiting in APPROVAL.
-- Legacy status values map 1:1 (DRAFT, ASSESSMENT, APPROVAL, SCHEDULED, IMPLEMENTED, FAILED, CANCELLED). impact does not exist in the legacy
-- data and stays NULL (nothing is invented). Data quality Q7: IMPLEMENTED/FAILED changes without actual_start keep actual_start NULL.
-- Legacy has no update timestamp: updated_at = coalesce(actual_end, actual_start, created_at).
SELECT format('INSERT INTO changes (change_id, change_no, company_id, title, description, change_type, status, risk_level, impact, requester_id, owner_team_id, planned_start, planned_end, actual_start, actual_end, rollback_plan, created_at, updated_at) VALUES (%s, %L, 1, %L, %L, %L, %L, %L, NULL, %s, %s, %s, %s, %s, %s, %L, %L, %L);',
              c.change_id, c.change_no, c.title, c.description, c.change_type, c.status, c.risk_level,
              coalesce(c.requester_id::text, '1'), coalesce(c.owner_team_id::text, 'NULL'),
              coalesce(quote_literal(c.planned_start::text), 'NULL'), coalesce(quote_literal(c.planned_end::text), 'NULL'),
              coalesce(quote_literal(c.actual_start::text), 'NULL'), coalesce(quote_literal(c.actual_end::text), 'NULL'),
              c.rollback_plan, c.created_at, coalesce(c.actual_end, c.actual_start, c.created_at))
FROM esmp.change_requests c ORDER BY c.change_id;
-- The legacy approvals table is empty (Q13): open step 1 (CHANGE_MANAGER) for changes waiting in APPROVAL (non-STANDARD; step 2 SERVICE_MANAGER follows for HIGH-risk NORMAL).
SELECT format('INSERT INTO change_approvals (change_id, step_order, approver_id, approver_role, decision, created_at) VALUES (%s, 1, NULL, ''CHANGE_MANAGER'', ''PENDING'', %L);',
              c.change_id, c.created_at)
FROM esmp.change_requests c WHERE c.status = 'APPROVAL' AND c.change_type <> 'STANDARD' ORDER BY c.change_id;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('changes','change_id'),('change_approvals','approval_id')) v(t, c);
