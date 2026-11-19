-- request-service demo seed: catalogue (one item per legacy service), approval steps, the 45 legacy requests, pending approvals.
-- Catalogue rules follow the previous product's demo config (BQ-5): line manager always; SERVICE_MANAGER when cost >= 1000.
-- Items reuse the service id as item id. Base cost: Laptop & Desktop and Cloud Hosting 1200, Access Management 0, others 150.
SELECT format('INSERT INTO catalogue_items (item_id, company_id, service_id, name, description, base_cost, fulfilment_team_id, active) VALUES (%s, 1, %s, %L, %L, %s, %s, %L);',
              s.service_id, s.service_id, 'Request: ' || s.name, 'Standard request for ' || s.name,
              CASE WHEN s.name IN ('Laptop & Desktop','Cloud Hosting') THEN 1200 WHEN s.name = 'Access Management' THEN 0 ELSE 150 END,
              coalesce(s.owning_team_id::text, 'NULL'), s.is_active)
FROM esmp.services s ORDER BY s.service_id;
SELECT format('INSERT INTO approval_steps (item_id, step_order, approver_type, approver_role, min_cost) VALUES (%s, 1, ''MANAGER'', NULL, 0);', service_id)
FROM esmp.services ORDER BY service_id;
SELECT format('INSERT INTO approval_steps (item_id, step_order, approver_type, approver_role, min_cost) VALUES (%s, 2, ''ROLE'', ''SERVICE_MANAGER'', 1000);', service_id)
FROM esmp.services ORDER BY service_id;
-- Data quality Q6: 8 FULFILLED requests have no fulfilled_at in the legacy data. They are kept as they are (fulfilled_at stays NULL).
SELECT format('INSERT INTO service_requests (request_id, request_no, company_id, requester_id, service_id, item_id, title, details, status, estimated_cost, assigned_team_id, requested_at, updated_at, fulfilled_at) VALUES (%s, %L, %s, %s, %s, %s, %L, %L, %L, %s, %s, %L, %L, %s);',
              r.request_id, r.request_no, coalesce(o.company_id, d.company_id, 1), r.requester_id,
              coalesce(r.service_id::text, 'NULL'), coalesce(r.service_id::text, 'NULL'), r.title, r.details, r.status,
              coalesce(r.estimated_cost::text, 'NULL'), coalesce(s.owning_team_id::text, 'NULL'), r.requested_at,
              coalesce(r.fulfilled_at, r.requested_at), coalesce(quote_literal(r.fulfilled_at::text), 'NULL'))
FROM esmp.service_requests r JOIN esmp.users u ON u.user_id = r.requester_id
LEFT JOIN esmp.offices o ON o.office_id = u.office_id LEFT JOIN esmp.departments d ON d.department_id = u.department_id
LEFT JOIN esmp.services s ON s.service_id = r.service_id ORDER BY r.request_id;
-- The legacy approvals table is empty (Q13): open step 1 for requests waiting for approval (manager, else SERVICE_MANAGER).
SELECT format('INSERT INTO request_approvals (request_id, step_order, approver_id, approver_role, decision, created_at) VALUES (%s, 1, %s, %s, ''PENDING'', %L);',
              r.request_id, coalesce(u.manager_id::text, 'NULL'), CASE WHEN u.manager_id IS NULL THEN '''SERVICE_MANAGER''' ELSE 'NULL' END, r.requested_at)
FROM esmp.service_requests r JOIN esmp.users u ON u.user_id = r.requester_id WHERE r.status = 'PENDING_APPROVAL' ORDER BY r.request_id;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('catalogue_items','item_id'),('service_requests','request_id'),('request_approvals','approval_id')) v(t, c);
