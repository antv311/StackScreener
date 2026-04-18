CREATE TABLE IF NOT EXISTS api_keys (
    api_uid   INTEGER PRIMARY KEY AUTOINCREMENT,

    user_uid  INTEGER NOT NULL REFERENCES users(user_uid),
    name      TEXT NOT NULL,    -- provider label: 'senate_watcher', 'sec_edgar', 'plaid', or any custom name
    api_key   TEXT NOT NULL,    -- Fernet-encrypted, never stored in plaintext
    url       TEXT,             -- base URL of the API endpoint (optional, for generic/custom providers)

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(user_uid, name)
);
