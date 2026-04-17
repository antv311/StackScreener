CREATE TABLE scans (
    scan_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    scan_mode    TEXT NOT NULL,  -- 'nsr', 'tase', 'watchlist', 'thematic', 'custom'
    triggered_by TEXT,           -- 'manual', 'scheduled', 'alert'
    status       TEXT NOT NULL DEFAULT 'running',  -- 'running', 'complete', 'failed'

    symbol_count  INTEGER,
    scored_count  INTEGER,
    failed_count  INTEGER,

    started_at   TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    notes        TEXT
);
