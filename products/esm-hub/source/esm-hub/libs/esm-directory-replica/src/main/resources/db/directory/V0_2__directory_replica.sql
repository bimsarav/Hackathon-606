-- Directory replica tables (esm-directory-replica). Filled only from the directory.* Kafka topics.
CREATE TABLE dir_users (
  user_id           BIGINT PRIMARY KEY,
  company_id        BIGINT       NOT NULL,
  employee_no       VARCHAR(20),
  first_name        VARCHAR(60)  NOT NULL,
  last_name         VARCHAR(60)  NOT NULL,
  email             VARCHAR(160) NOT NULL,
  office_id         BIGINT,
  department_id     BIGINT,
  manager_id        BIGINT,
  employment_status VARCHAR(20)  NOT NULL,
  roles             VARCHAR(500) NOT NULL DEFAULT ''   -- comma-separated role names
);
CREATE INDEX idx_dir_users_company ON dir_users (company_id);

CREATE TABLE dir_teams (
  team_id         BIGINT PRIMARY KEY,
  company_id      BIGINT       NOT NULL,
  name            VARCHAR(100) NOT NULL,
  support_level   INTEGER      NOT NULL,
  manager_user_id BIGINT,
  active          BOOLEAN      NOT NULL
);

CREATE TABLE dir_team_members (
  team_id BIGINT NOT NULL REFERENCES dir_teams ON DELETE CASCADE,
  user_id BIGINT NOT NULL,
  PRIMARY KEY (team_id, user_id)
);

CREATE TABLE dir_services (
  service_id     BIGINT PRIMARY KEY,
  company_id     BIGINT       NOT NULL,
  name           VARCHAR(120) NOT NULL,
  category_id    BIGINT,
  category_name  VARCHAR(80),
  owning_team_id BIGINT,
  active         BOOLEAN      NOT NULL
);

CREATE TABLE dir_offices (
  office_id  BIGINT PRIMARY KEY,
  company_id BIGINT       NOT NULL,
  name       VARCHAR(100) NOT NULL,
  city       VARCHAR(80),
  country    VARCHAR(80),
  timezone   VARCHAR(60)  NOT NULL
);
