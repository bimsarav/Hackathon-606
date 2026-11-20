-- asset-service demo seed: the 60 legacy assets (all belong to company 1) plus one open assignment per ASSIGNED asset.
-- The legacy dump stores only the current assignee, so the history table is seeded from the current state:
-- assigned_at = the asset's created_at (no earlier date is known), assigned_by is unknown (NULL), returned_at NULL.
-- updated_at = created_at (the legacy table has no update timestamp). Legacy IDs are kept.
SELECT format('INSERT INTO assets (asset_id, company_id, asset_tag, asset_type, manufacturer, model, serial_number, purchase_date, warranty_end, office_id, assigned_user_id, asset_status, purchase_cost, created_at, updated_at) VALUES (%s, 1, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L);',
              asset_id, asset_tag, asset_type, manufacturer, model, serial_number, purchase_date, warranty_end,
              office_id, assigned_user_id, asset_status, purchase_cost, created_at, created_at)
FROM esmp.assets ORDER BY asset_id;
SELECT format('INSERT INTO asset_assignments (asset_id, user_id, assigned_at, returned_at, assigned_by) VALUES (%s, %s, %L, NULL, NULL);',
              asset_id, assigned_user_id, created_at)
FROM esmp.assets WHERE assigned_user_id IS NOT NULL ORDER BY asset_id;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('assets', 'asset_id'), ('asset_assignments', 'assignment_id')) v(t, c);
