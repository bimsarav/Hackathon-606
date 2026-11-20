-- incident-service demo seed: SLA policies, the 150 legacy incidents with comments, worklogs, a timeline, 12 problems and 37 links.
-- Priorities, statuses, workflow, calendars and escalation rules are install-wide reference data in V2 (not seeded here).
-- Directory data (users, teams, services) arrives through the replica topics.
-- Handling of data-quality findings (docs/data/data-quality-report.md):
--   Q15 due_at is kept as supplied (calendar-time); response_due_at is derived from the policy response target (calendar time).
--   Q1/Q2 comment and worklog timestamps are kept as supplied. Q3/Q4 legacy assignees are kept as supplied (the API enforces the rules).
--   Breach flags are precomputed as of 2026-11-18 so the first SLA scan does not escalate history.
-- Legacy policies are install-wide (company_id NULL) and keep their IDs.
SELECT format('INSERT INTO sla_policies (sla_id, company_id, name, priority_id, service_id, business_hours_only, response_target_minutes, resolution_target_minutes, effective_from, effective_to, version) VALUES (%s, NULL, %L, %s, %s, %L, %s, %s, %L, %s, 1);',
              sla_id, name, priority_id, coalesce(service_id::text, 'NULL'), business_hours_only, response_target_minutes,
              resolution_target_minutes, effective_from, coalesce(quote_literal(effective_to::text), 'NULL'))
FROM esmp.sla_policies ORDER BY sla_id;

WITH asof AS (SELECT TIMESTAMPTZ '2026-11-18 00:00:00+00' AS t),
base AS (
  SELECT i.*, coalesce(o.company_id, d.company_id, 1) AS company_id,
         coalesce(i.closed_at, i.resolved_at, i.first_response_at, i.created_at) AS updated_at,
         i.created_at + make_interval(mins => coalesce(s.response_target_minutes, p.response_minutes)) AS response_due_at
  FROM esmp.incidents i
  JOIN esmp.users u ON u.user_id = i.requester_id
  LEFT JOIN esmp.offices o ON o.office_id = u.office_id
  LEFT JOIN esmp.departments d ON d.department_id = u.department_id
  LEFT JOIN esmp.sla_policies s ON s.sla_id = i.sla_id
  JOIN esmp.priorities p ON p.priority_id = i.priority_id)
SELECT format('INSERT INTO incidents (incident_id, company_id, ticket_no, title, description, requester_id, service_id, asset_id, priority_id, status_id, assigned_team_id, assigned_user_id, sla_id, channel, created_at, updated_at, first_response_at, resolved_at, closed_at, response_due_at, due_at, sla_paused_since, sla_paused_minutes, response_breached, resolution_breached, satisfaction_score, reopened_count) VALUES (%s, %s, %L, %L, %L, %s, %s, %s, %s, %s, %s, %s, %s, %L, %L, %L, %s, %s, %s, %L, %s, %s, 0, %L, %L, %s, %s);',
              b.incident_id, b.company_id, b.ticket_no, b.title, b.description, b.requester_id,
              coalesce(b.service_id::text, 'NULL'), coalesce(b.asset_id::text, 'NULL'), b.priority_id, b.status_id,
              coalesce(b.assigned_team_id::text, 'NULL'), coalesce(b.assigned_user_id::text, 'NULL'), coalesce(b.sla_id::text, 'NULL'),
              b.channel, b.created_at, b.updated_at,
              coalesce(quote_literal(b.first_response_at::text), 'NULL'), coalesce(quote_literal(b.resolved_at::text), 'NULL'),
              coalesce(quote_literal(b.closed_at::text), 'NULL'), b.response_due_at, coalesce(quote_literal(b.due_at::text), 'NULL'),
              CASE WHEN b.status_id = 4 THEN quote_literal(b.updated_at::text) ELSE 'NULL' END,
              CASE WHEN b.first_response_at IS NULL THEN b.status_id < 5 AND a.t > b.response_due_at
                   ELSE b.first_response_at > b.response_due_at END,
              CASE WHEN b.status_id = 7 THEN false
                   WHEN b.status_id >= 5 THEN coalesce(b.resolved_at, b.closed_at) > b.due_at
                   ELSE a.t > b.due_at END,
              coalesce(b.satisfaction_score::text, 'NULL'), b.reopened_count)
FROM base b, asof a ORDER BY b.incident_id;

SELECT format('INSERT INTO incident_comments (comment_id, incident_id, author_id, body, is_internal, created_at) VALUES (%s, %s, %s, %L, %L, %L);',
              comment_id, incident_id, author_id, body, is_internal, created_at)
FROM esmp.incident_comments ORDER BY comment_id;
SELECT format('INSERT INTO worklogs (worklog_id, incident_id, user_id, minutes_spent, work_description, logged_at) VALUES (%s, %s, %s, %s, %L, %L);',
              worklog_id, incident_id, user_id, minutes_spent, work_description, logged_at)
FROM esmp.worklogs ORDER BY worklog_id;

-- Timeline reconstructed from the incident timestamps (the legacy data has no event history).
SELECT format('INSERT INTO incident_events (incident_id, event_type, from_value, to_value, actor_id, occurred_at) VALUES (%s, %L, %s, %s, %s, %L);',
              incident_id, event_type, coalesce(quote_literal(from_value), 'NULL'), coalesce(quote_literal(to_value), 'NULL'),
              coalesce(actor::text, 'NULL'), occurred_at)
FROM (
  SELECT incident_id, 'CREATED' AS event_type, NULL::text AS from_value, ticket_no AS to_value, requester_id AS actor, created_at AS occurred_at, 1 AS ord FROM esmp.incidents
  UNION ALL
  SELECT incident_id, 'STATUS_CHANGE', 'NEW', 'IN_PROGRESS', assigned_user_id, first_response_at, 2 FROM esmp.incidents WHERE first_response_at IS NOT NULL
  UNION ALL
  SELECT incident_id, 'STATUS_CHANGE', 'IN_PROGRESS', 'RESOLVED', assigned_user_id, resolved_at, 3 FROM esmp.incidents WHERE resolved_at IS NOT NULL
  UNION ALL
  SELECT incident_id, 'STATUS_CHANGE', 'RESOLVED', 'CLOSED', NULL, closed_at, 4 FROM esmp.incidents WHERE closed_at IS NOT NULL
) e ORDER BY incident_id, occurred_at, ord;

SELECT format('INSERT INTO problems (problem_id, company_id, problem_no, title, description, status, root_cause, workaround, known_error, owner_team_id, created_at, updated_at, resolved_at) VALUES (%s, 1, %L, %L, %L, %L, %L, %L, %L, %s, %L, %L, %s);',
              problem_id, problem_no, title, description, status, root_cause, workaround, known_error,
              coalesce(owner_team_id::text, 'NULL'), created_at, coalesce(resolved_at, created_at),
              coalesce(quote_literal(resolved_at::text), 'NULL'))
FROM esmp.problems ORDER BY problem_id;
SELECT format('INSERT INTO incident_problem_links (incident_id, problem_id) VALUES (%s, %s);', incident_id, problem_id)
FROM esmp.incident_problem_links ORDER BY problem_id, incident_id;

SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('sla_policies','sla_id'),('incidents','incident_id'),('incident_comments','comment_id'),('worklogs','worklog_id'),
             ('problems','problem_id'),('incident_events','event_id')) v(t, c);
