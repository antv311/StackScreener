CREATE TABLE IF NOT EXISTS settings (
    setting_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uid     INTEGER NOT NULL REFERENCES users(user_uid),
    key          TEXT NOT NULL,
    value        TEXT,
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_uid, key)
);
