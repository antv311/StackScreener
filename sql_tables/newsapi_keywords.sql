CREATE TABLE IF NOT EXISTS newsapi_keywords (
    keyword_uid INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uid    INTEGER NOT NULL REFERENCES users(user_uid),
    keyword     TEXT NOT NULL,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_uid, keyword)
);
