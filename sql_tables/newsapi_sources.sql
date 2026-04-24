CREATE TABLE IF NOT EXISTS newsapi_sources (
    source_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uid    INTEGER NOT NULL REFERENCES users(user_uid),
    source_id   TEXT NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT,
    country     TEXT,
    language    TEXT,
    enabled     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_uid, source_id)
);
