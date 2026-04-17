CREATE TABLE IF NOT EXISTS api_keys (
    api_uid   INTEGER PRIMARY KEY AUTOINCREMENT,

    user_uid  INTEGER NOT NULL REFERENCES users(user_uid),
    name      TEXT NOT NULL,       -- 'finviz', 'unusual_whales', 'quiver_quant', 'plaid'
    api_key   TEXT NOT NULL,       -- Fernet-encrypted, never stored in plaintext

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(user_uid, name)
);
