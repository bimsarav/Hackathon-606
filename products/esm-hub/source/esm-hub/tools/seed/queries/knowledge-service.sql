-- knowledge-service demo seed: the 15 legacy knowledge articles (company 1).
-- Repairs / mapping (the target schema enforces the four-eyes workflow):
--   * published_at is kept only for PUBLISHED rows; the legacy dump carries one on DRAFT / UNDER_REVIEW rows, which would
--     contradict their status, so it is dropped (NULL).
--   * reviewed_by: PUBLISHED articles were reviewed by user 8 (the only KNOWLEDGE_EDITOR; never the author), others NULL.
--   * not_helpful_count = 0 (the legacy table has no such column). created_at = published_at when present, else a fixed
--     reference instant; updated_at = created_at. No feedback rows (none in the dump).
SELECT format('INSERT INTO articles (article_id, company_id, title, body, category_id, author_id, reviewed_by, status, view_count, helpful_count, not_helpful_count, published_at, created_at, updated_at) VALUES (%s, 1, %L, %L, %L, %L, %L, %L, %s, %s, 0, %L, %L, %L);',
              article_id, title, body, category_id, author_id,
              CASE WHEN status = 'PUBLISHED' THEN 8 END, status, view_count, helpful_count,
              CASE WHEN status = 'PUBLISHED' THEN published_at END,
              coalesce(published_at, timestamptz '2026-01-01 00:00:00+00'),
              coalesce(published_at, timestamptz '2026-01-01 00:00:00+00'))
FROM esmp.knowledge_articles ORDER BY article_id;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('articles', 'article_id')) v(t, c);
