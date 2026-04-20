-- database/schema.sql
-- Full DDL for all Software Aging Analyzer tables

-- System-level metrics snapshot
CREATE TABLE IF NOT EXISTS system_metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        REAL    NOT NULL,
    cpu              REAL    NOT NULL,
    ram              REAL    NOT NULL,
    ram_used         REAL    NOT NULL,
    ram_available    REAL    NOT NULL,
    disk             REAL    NOT NULL,
    disk_read_rate   REAL    NOT NULL DEFAULT 0,
    disk_write_rate  REAL    NOT NULL DEFAULT 0,
    net_send_rate    REAL    NOT NULL DEFAULT 0,
    net_recv_rate    REAL    NOT NULL DEFAULT 0,
    load_avg         REAL    NOT NULL DEFAULT 0,
    context_switches REAL    NOT NULL DEFAULT 0,
    interrupt_rate   REAL    NOT NULL DEFAULT 0
);

-- Per-process metrics snapshot
CREATE TABLE IF NOT EXISTS process_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL    NOT NULL,
    pid         INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    cpu         REAL    NOT NULL DEFAULT 0,
    memory      REAL    NOT NULL DEFAULT 0,
    memory_bytes INTEGER NOT NULL DEFAULT 0,
    threads     INTEGER NOT NULL DEFAULT 0,
    fds         INTEGER NOT NULL DEFAULT 0
);

-- Baseline reference values (single row, upserted)
CREATE TABLE IF NOT EXISTS baseline (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    cpu_baseline  REAL NOT NULL DEFAULT 0,
    ram_baseline  REAL NOT NULL DEFAULT 0,
    disk_baseline REAL NOT NULL DEFAULT 0,
    captured_at   REAL NOT NULL DEFAULT 0
);

-- Failure probability predictions over time
CREATE TABLE IF NOT EXISTS predictions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             REAL NOT NULL,
    failure_probability   REAL NOT NULL,
    predicted_restart_time REAL,
    predicted_crash_time   REAL,
    lambda_val            REAL NOT NULL DEFAULT 0,
    priority              TEXT NOT NULL DEFAULT 'LOW'
);

-- Root cause analysis results
CREATE TABLE IF NOT EXISTS root_cause (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL    NOT NULL,
    pid       INTEGER NOT NULL DEFAULT 0,
    name      TEXT    NOT NULL DEFAULT 'system',
    cause     TEXT    NOT NULL,
    severity  TEXT    NOT NULL DEFAULT 'LOW',
    detail    TEXT    NOT NULL DEFAULT ''
);

-- Prevention / mitigation recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      REAL    NOT NULL,
    recommendation TEXT    NOT NULL,
    priority       TEXT    NOT NULL DEFAULT 'MEDIUM',
    related_cause  TEXT    NOT NULL DEFAULT ''
);

-- Action queue for auto-remediation prompts/executions
CREATE TABLE IF NOT EXISTS action_queue (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  REAL    NOT NULL,
    action     TEXT    NOT NULL,
    target     TEXT    NOT NULL,
    pid        INTEGER DEFAULT NULL,
    params_json TEXT   NOT NULL DEFAULT '{}',
    source     TEXT    NOT NULL DEFAULT '',
    reason     TEXT    NOT NULL DEFAULT '',
    severity   TEXT    NOT NULL DEFAULT 'LOW',
    status     TEXT    NOT NULL DEFAULT 'PENDING',
    message    TEXT    NOT NULL DEFAULT '',
    executed_at REAL   DEFAULT NULL
);

-- Indexes for fast time-range queries
CREATE INDEX IF NOT EXISTS idx_sys_ts  ON system_metrics  (timestamp);
CREATE INDEX IF NOT EXISTS idx_proc_ts ON process_metrics (timestamp);
CREATE INDEX IF NOT EXISTS idx_pred_ts ON predictions     (timestamp);
CREATE INDEX IF NOT EXISTS idx_rc_ts   ON root_cause      (timestamp);
CREATE INDEX IF NOT EXISTS idx_rec_ts  ON recommendations (timestamp);
CREATE INDEX IF NOT EXISTS idx_action_ts ON action_queue  (timestamp);

-- Notification log — tracks every toast sent (for cooldown / dedup)
CREATE TABLE IF NOT EXISTS notification_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  REAL    NOT NULL,
    category   TEXT    NOT NULL,          -- root_cause | prediction | recommendation | degradation | health_summary
    severity   TEXT    NOT NULL DEFAULT 'LOW',
    target     TEXT    NOT NULL DEFAULT 'system',
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    cooldown_key TEXT  NOT NULL DEFAULT ''  -- unique key for dedup: e.g. "root_cause:chrome.exe:Memory Leak"
);

-- User notification preferences (single row, upserted like baseline)
CREATE TABLE IF NOT EXISTS notification_settings (
    id               INTEGER PRIMARY KEY DEFAULT 1,
    enabled          INTEGER NOT NULL DEFAULT 1,    -- 0 = off, 1 = on
    cooldown_sec     INTEGER NOT NULL DEFAULT 600,
    min_severity     TEXT    NOT NULL DEFAULT 'LOW',
    alert_types_json TEXT    NOT NULL DEFAULT '{}',  -- JSON of category → bool
    updated_at       REAL    NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_notif_ts   ON notification_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_notif_key  ON notification_log (cooldown_key, timestamp);
