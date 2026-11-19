-- reporting-service read model (CQRS). Rows are upserted from the compacted state topics; a tombstone deletes the row.
-- Names (teams, users, offices, services) come from the directory replica tables in the same database.
CREATE TABLE rpt_incidents (
  incident_id         BIGINT PRIMARY KEY,
  company_id          BIGINT       NOT NULL,
  ticket_no           VARCHAR(30),
  title               VARCHAR(300),
  status              VARCHAR(40),
  closed              BOOLEAN      NOT NULL,
  priority            VARCHAR(20),
  service_id          BIGINT,
  channel             VARCHAR(30),
  requester_id        BIGINT,
  assigned_team_id    BIGINT,
  assigned_user_id    BIGINT,
  created_at          TIMESTAMPTZ  NOT NULL,
  first_response_at   TIMESTAMPTZ,
  resolved_at         TIMESTAMPTZ,
  closed_at           TIMESTAMPTZ,
  response_due_at     TIMESTAMPTZ,
  due_at              TIMESTAMPTZ,
  response_breached   BOOLEAN      NOT NULL,
  resolution_breached BOOLEAN      NOT NULL,
  sla_paused          BOOLEAN      NOT NULL,
  reopened_count      INTEGER      NOT NULL,
  satisfaction_score  INTEGER,
  worklog_minutes     INTEGER      NOT NULL
);
CREATE INDEX idx_rpt_incidents_company_created ON rpt_incidents (company_id, created_at);

CREATE TABLE rpt_problems (
  problem_id    BIGINT PRIMARY KEY,
  company_id    BIGINT      NOT NULL,
  problem_no    VARCHAR(30),
  title         VARCHAR(300),
  status        VARCHAR(40),
  known_error   BOOLEAN     NOT NULL,
  owner_team_id BIGINT,
  created_at    TIMESTAMPTZ,
  resolved_at   TIMESTAMPTZ
);
CREATE INDEX idx_rpt_problems_company ON rpt_problems (company_id);

CREATE TABLE rpt_problem_incidents (
  problem_id  BIGINT NOT NULL REFERENCES rpt_problems ON DELETE CASCADE,
  incident_id BIGINT NOT NULL,
  PRIMARY KEY (problem_id, incident_id)
);
CREATE INDEX idx_rpt_problem_incidents_incident ON rpt_problem_incidents (incident_id);

CREATE TABLE rpt_requests (
  request_id       BIGINT PRIMARY KEY,
  company_id       BIGINT      NOT NULL,
  request_no       VARCHAR(30),
  title            VARCHAR(300),
  status           VARCHAR(40),
  requester_id     BIGINT,
  service_id       BIGINT,
  item_id          BIGINT,
  estimated_cost   NUMERIC(14, 2),
  assigned_team_id BIGINT,
  requested_at     TIMESTAMPTZ,
  approved_at      TIMESTAMPTZ,
  fulfilled_at     TIMESTAMPTZ
);
CREATE INDEX idx_rpt_requests_company ON rpt_requests (company_id, requested_at);

CREATE TABLE rpt_changes (
  change_id     BIGINT PRIMARY KEY,
  company_id    BIGINT      NOT NULL,
  change_no     VARCHAR(30),
  title         VARCHAR(300),
  change_type   VARCHAR(30),
  status        VARCHAR(40),
  risk_level    VARCHAR(30),
  impact        VARCHAR(30),
  owner_team_id BIGINT,
  requester_id  BIGINT,
  planned_start TIMESTAMPTZ,
  planned_end   TIMESTAMPTZ,
  actual_start  TIMESTAMPTZ,
  actual_end    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ
);
CREATE INDEX idx_rpt_changes_company ON rpt_changes (company_id);

CREATE TABLE rpt_assets (
  asset_id         BIGINT PRIMARY KEY,
  company_id       BIGINT      NOT NULL,
  asset_tag        VARCHAR(40),
  asset_type       VARCHAR(40),
  status           VARCHAR(40),
  assigned_user_id BIGINT,
  office_id        BIGINT,
  purchase_date    DATE,
  warranty_end     DATE,
  purchase_cost    NUMERIC(14, 2)
);
CREATE INDEX idx_rpt_assets_company ON rpt_assets (company_id);
