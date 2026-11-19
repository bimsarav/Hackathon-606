SET search_path TO esmp;
\pset footer off
\echo == status x timestamps
SELECT s.name, count(*), count(first_response_at) fr, count(resolved_at) res, count(closed_at) clo, count(assigned_user_id) au, count(assigned_team_id) at, count(due_at) due, count(sla_id) sla, count(satisfaction_score) csat
FROM incidents i JOIN ticket_statuses s USING(status_id) GROUP BY 1 ORDER BY 1;
\echo == inconsistent states
SELECT 'resolved_before_created', count(*) FROM incidents WHERE resolved_at < created_at
UNION ALL SELECT 'response_before_created', count(*) FROM incidents WHERE first_response_at < created_at
UNION ALL SELECT 'closed_before_resolved', count(*) FROM incidents WHERE closed_at < resolved_at
UNION ALL SELECT 'open_with_resolved_at', count(*) FROM incidents i JOIN ticket_statuses s USING(status_id) WHERE NOT s.is_closed AND resolved_at IS NOT NULL
UNION ALL SELECT 'closed_status_no_resolved', count(*) FROM incidents i JOIN ticket_statuses s USING(status_id) WHERE s.name IN ('RESOLVED','CLOSED') AND resolved_at IS NULL
UNION ALL SELECT 'assigned_user_not_in_team', count(*) FROM incidents i WHERE assigned_user_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM team_members tm WHERE tm.team_id=i.assigned_team_id AND tm.user_id=i.assigned_user_id)
UNION ALL SELECT 'sla_priority_mismatch', count(*) FROM incidents i JOIN sla_policies p USING(sla_id) WHERE p.priority_id<>i.priority_id
UNION ALL SELECT 'due_mismatch_resolution_target', count(*) FROM incidents i JOIN priorities p USING(priority_id) WHERE due_at IS NOT NULL AND due_at <> created_at + p.resolution_minutes*interval '1 minute'
UNION ALL SELECT 'csat_on_open', count(*) FROM incidents i JOIN ticket_statuses s USING(status_id) WHERE NOT s.is_closed AND satisfaction_score IS NOT NULL
UNION ALL SELECT 'comment_before_incident', count(*) FROM incident_comments c JOIN incidents i USING(incident_id) WHERE c.created_at < i.created_at
UNION ALL SELECT 'worklog_before_incident', count(*) FROM worklogs w JOIN incidents i USING(incident_id) WHERE w.logged_at < i.created_at
UNION ALL SELECT 'asset_assigned_status_no_user', count(*) FROM assets WHERE asset_status='ASSIGNED' AND assigned_user_id IS NULL
UNION ALL SELECT 'asset_user_but_not_assigned', count(*) FROM assets WHERE asset_status<>'ASSIGNED' AND assigned_user_id IS NOT NULL
UNION ALL SELECT 'warranty_before_purchase', count(*) FROM assets WHERE warranty_end < purchase_date
UNION ALL SELECT 'asset_null_serial', count(*) FROM assets WHERE serial_number IS NULL
UNION ALL SELECT 'request_fulfilled_before', count(*) FROM service_requests WHERE fulfilled_at < requested_at
UNION ALL SELECT 'change_end_before_start', count(*) FROM change_requests WHERE planned_end < planned_start OR actual_end < actual_start
UNION ALL SELECT 'kb_published_no_date', count(*) FROM knowledge_articles WHERE status='PUBLISHED' AND published_at IS NULL
UNION ALL SELECT 'kb_helpful_gt_views', count(*) FROM knowledge_articles WHERE helpful_count > view_count
UNION ALL SELECT 'notif_sent_status_no_sent_at', count(*) FROM notifications WHERE delivery_status='SENT' AND sent_at IS NULL
UNION ALL SELECT 'users_inactive_with_open_tickets', count(DISTINCT requester_id) FROM incidents i JOIN users u ON u.user_id=i.requester_id JOIN ticket_statuses s USING(status_id) WHERE NOT s.is_closed AND u.employment_status<>'ACTIVE'
UNION ALL SELECT 'users_without_roles', count(*) FROM users u WHERE NOT EXISTS (SELECT 1 FROM user_roles r WHERE r.user_id=u.user_id)
UNION ALL SELECT 'dup_name_users', count(*) FROM (SELECT first_name,last_name FROM users GROUP BY 1,2 HAVING count(*)>1) x
UNION ALL SELECT 'problems_no_incidents', count(*) FROM problems p WHERE NOT EXISTS (SELECT 1 FROM incident_problem_links l WHERE l.problem_id=p.problem_id)
UNION ALL SELECT 'seq_behind_users', (SELECT CASE WHEN last_value < (SELECT max(user_id) FROM users) THEN 1 ELSE 0 END FROM users_user_id_seq);
\echo == distinct enums
SELECT 'sr.status', status, count(*) FROM service_requests GROUP BY 2
UNION ALL SELECT 'cr.status', status, count(*) FROM change_requests GROUP BY 2
UNION ALL SELECT 'cr.risk', coalesce(risk_level,'<null>'), count(*) FROM change_requests GROUP BY 2
UNION ALL SELECT 'pb.status', status, count(*) FROM problems GROUP BY 2
UNION ALL SELECT 'kb.status', status, count(*) FROM knowledge_articles GROUP BY 2
UNION ALL SELECT 'nt.channel', channel, count(*) FROM notifications GROUP BY 2
UNION ALL SELECT 'nt.status', delivery_status, count(*) FROM notifications GROUP BY 2
UNION ALL SELECT 'in.channel', channel, count(*) FROM incidents GROUP BY 2
UNION ALL SELECT 'as.status', asset_status, count(*) FROM assets GROUP BY 2
UNION ALL SELECT 'as.type', asset_type, count(*) FROM assets GROUP BY 2
UNION ALL SELECT 'au.action', entity_type||':'||action, count(*) FROM audit_logs GROUP BY 2
UNION ALL SELECT 'emp', employment_status, count(*) FROM users GROUP BY 2
ORDER BY 1,2;
\echo == date ranges
SELECT min(created_at), max(created_at) FROM incidents;
SELECT r.role_name, count(*) FROM user_roles ur JOIN roles r USING(role_id) GROUP BY 1 ORDER BY 1;
SELECT * FROM sla_policies; SELECT service_id,name,owning_team_id,category_id,is_active FROM services;
\echo == SLA breach by priority (calendar time)
SELECT p.name, count(*) n, round(avg(extract(epoch from first_response_at-created_at)/60)) avg_resp_min, p.response_minutes,
 sum((first_response_at-created_at > p.response_minutes*interval '1 min')::int) resp_breach,
 round(avg(extract(epoch from resolved_at-created_at)/60)) avg_res_min, p.resolution_minutes,
 sum((resolved_at-created_at > p.resolution_minutes*interval '1 min')::int) res_breach
FROM incidents i JOIN priorities p USING(priority_id) GROUP BY p.priority_id,p.name ORDER BY 1;
