-- esm-common tables, present in every service database (classpath:db/common).
CREATE TABLE outbox_events (
  id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id       UUID         NOT NULL UNIQUE,
  topic          VARCHAR(120) NOT NULL,
  message_key    VARCHAR(120) NOT NULL,
  event_type     VARCHAR(120) NOT NULL,
  payload        TEXT,                       -- JSON envelope; NULL = tombstone
  correlation_id VARCHAR(64),
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
  published_at   TIMESTAMPTZ,
  attempts       INTEGER      NOT NULL DEFAULT 0,
  last_error     VARCHAR(500)
);
CREATE INDEX idx_outbox_unpublished ON outbox_events (id) WHERE published_at IS NULL;

CREATE TABLE processed_events (
  event_id     UUID         NOT NULL,
  consumer     VARCHAR(120) NOT NULL,
  processed_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
  PRIMARY KEY (event_id, consumer)
);

CREATE TABLE snapshot_state (
  name         VARCHAR(120) PRIMARY KEY,
  version      INTEGER      NOT NULL,
  published_at TIMESTAMPTZ
);
