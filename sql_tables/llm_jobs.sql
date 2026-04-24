CREATE TABLE IF NOT EXISTS llm_jobs (
    job_uid      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type     TEXT NOT NULL,   -- 'classify_news' | 'extract_10k' | 'parse_8k'
    input_json   TEXT NOT NULL,   -- JSON payload for the job
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending|running|done|failed|paused|cancelled
    result_json  TEXT,            -- JSON output on success
    error_text   TEXT,            -- error message on failure
    retries      INTEGER NOT NULL DEFAULT 0,
    priority     INTEGER NOT NULL DEFAULT 5,  -- 1=high … 9=low
    source_ref   TEXT,            -- e.g. 'article_uid:42' or 'cik:0001234'
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    started_at   TEXT,
    completed_at TEXT
);
