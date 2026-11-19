-- Install-wide reference data every installation needs: priorities, statuses, workflow, business calendars with
-- sample 2026 holidays, timezone -> calendar mapping and default escalation rules. All of it is editable data
-- (requirements-analysis §5: BQ-1, BQ-2, BQ-4).

INSERT INTO priorities (priority_id, name, response_minutes, resolution_minutes) VALUES
 (1,'P1',15,240),(2,'P2',30,480),(3,'P3',240,2880),(4,'P4',480,5760);

INSERT INTO ticket_statuses (status_id, name, is_closed, pauses_sla) VALUES
 (1,'NEW',FALSE,FALSE),(2,'ASSIGNED',FALSE,FALSE),(3,'IN_PROGRESS',FALSE,FALSE),(4,'PENDING_USER',FALSE,TRUE),
 (5,'RESOLVED',TRUE,FALSE),(6,'CLOSED',TRUE,FALSE),(7,'CANCELLED',TRUE,FALSE);

INSERT INTO status_transitions (from_status_id, to_status_id) VALUES
 (1,2),(1,3),(1,7),
 (2,3),(2,4),(2,5),(2,7),
 (3,2),(3,4),(3,5),
 (4,3),(4,5),(4,7),
 (5,6),(5,3);

INSERT INTO business_calendars (name, timezone) VALUES
 ('UAE Business Hours','Asia/Dubai'),('UK Business Hours','Europe/London'),('Sri Lanka Business Hours','Asia/Colombo');

INSERT INTO calendar_hours (calendar_id, weekday, start_time, end_time)
SELECT c.calendar_id, d.wd, h.s, h.e
FROM business_calendars c
JOIN (VALUES ('UAE Business Hours', TIME '08:00', TIME '17:00'),
             ('UK Business Hours', TIME '09:00', TIME '17:30'),
             ('Sri Lanka Business Hours', TIME '08:30', TIME '17:00')) AS h(n, s, e) ON h.n = c.name
CROSS JOIN generate_series(0, 4) AS d(wd);

-- Sample public holidays for 2026: illustrative only, to be confirmed by HR (BQ-1)
INSERT INTO calendar_holidays (calendar_id, holiday_date, name)
SELECT c.calendar_id, v.d, v.n FROM business_calendars c JOIN (VALUES
  ('UAE Business Hours', DATE '2026-01-01', 'New Year''s Day'),
  ('UAE Business Hours', DATE '2026-12-02', 'National Day'),
  ('UAE Business Hours', DATE '2026-12-03', 'National Day holiday'),
  ('UK Business Hours', DATE '2026-01-01', 'New Year''s Day'),
  ('UK Business Hours', DATE '2026-04-03', 'Good Friday'),
  ('UK Business Hours', DATE '2026-04-06', 'Easter Monday'),
  ('UK Business Hours', DATE '2026-05-04', 'Early May bank holiday'),
  ('UK Business Hours', DATE '2026-05-25', 'Spring bank holiday'),
  ('UK Business Hours', DATE '2026-08-31', 'Summer bank holiday'),
  ('UK Business Hours', DATE '2026-12-25', 'Christmas Day'),
  ('UK Business Hours', DATE '2026-12-28', 'Boxing Day (substitute)'),
  ('Sri Lanka Business Hours', DATE '2026-02-04', 'Independence Day'),
  ('Sri Lanka Business Hours', DATE '2026-04-14', 'Sinhala and Tamil New Year'),
  ('Sri Lanka Business Hours', DATE '2026-05-01', 'May Day'),
  ('Sri Lanka Business Hours', DATE '2026-12-25', 'Christmas Day')
) AS v(cn, d, n) ON v.cn = c.name;

-- Office timezones map to the calendar of the same timezone
INSERT INTO timezone_calendars (timezone, calendar_id) SELECT timezone, calendar_id FROM business_calendars;

INSERT INTO escalation_rules (priority_id, trigger_type, notify_role) VALUES
  (1,'RESPONSE_BREACH','TEAM_LEAD'), (2,'RESPONSE_BREACH','TEAM_LEAD'),
  (NULL,'RESOLUTION_AT_RISK','TEAM_LEAD'),
  (1,'RESOLUTION_BREACH','SERVICE_MANAGER'), (2,'RESOLUTION_BREACH','SERVICE_MANAGER'),
  (3,'RESOLUTION_BREACH','TEAM_LEAD'), (4,'RESOLUTION_BREACH','TEAM_LEAD');
