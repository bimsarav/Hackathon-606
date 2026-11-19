-- notification-service demo seed: the 60 legacy notifications (all users belong to company 1 in the legacy data).
-- Status mapping:
--   IN_APP: always DELIVERED (an in-app notification is stored, hence delivered, at once; legacy PENDING/FAILED in-app rows
--           are an artefact of the generator).
--   EMAIL : SENT/DELIVERED -> SENT; PENDING -> PENDING (the sender picks it up, next_attempt_at = now);
--           FAILED -> FAILED with attempts = 1 and an immediate retry.
-- sent_at is kept as in the dump for SENT/DELIVERED rows. Data-quality Q8 (SENT without sent_at, 3 rows) is KEPT as is:
-- the row stays SENT with sent_at NULL (no timestamp is invented). PENDING/FAILED rows carry a legacy sent_at
-- that contradicts their status; it is dropped (set NULL).
SELECT format('INSERT INTO notifications (notification_id, company_id, user_id, channel, subject, body, delivery_status, attempts, last_error, created_at, sent_at, next_attempt_at) VALUES (%s, 1, %s, %L, %L, %L, %L, %s, %L, %L, %L, now());',
              notification_id, user_id, channel, subject, body,
              CASE WHEN channel = 'IN_APP' THEN 'DELIVERED'
                   WHEN delivery_status IN ('SENT', 'DELIVERED') THEN 'SENT'
                   ELSE delivery_status END,
              CASE WHEN channel = 'EMAIL' AND delivery_status = 'FAILED' THEN 1 ELSE 0 END,
              CASE WHEN channel = 'EMAIL' AND delivery_status = 'FAILED' THEN 'legacy delivery failure' END,
              coalesce(sent_at, now()),
              CASE WHEN channel = 'IN_APP' OR delivery_status IN ('SENT', 'DELIVERED') THEN sent_at END)
FROM esmp.notifications ORDER BY notification_id;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('notifications', 'notification_id')) v(t, c);
