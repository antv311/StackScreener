CREATE TABLE IF NOT EXISTS scheduled_jobs (
    schedule_uid    INTEGER PRIMARY KEY AUTOINCREMENT,
    label           TEXT NOT NULL,          -- human label matching _COMMANDS button label
    command_key     TEXT NOT NULL,          -- argv[1] fragment used as stable lookup key
    interval_hours  REAL NOT NULL DEFAULT 24,
    enabled         INTEGER NOT NULL DEFAULT 1,
    last_run_at     TEXT,                   -- ISO datetime of last execution; NULL = never run
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled ON scheduled_jobs (enabled, last_run_at);
