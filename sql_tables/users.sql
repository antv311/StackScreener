CREATE TABLE IF NOT EXISTS users (
    user_uid      INTEGER PRIMARY KEY AUTOINCREMENT,

    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,

    display_name  TEXT,
    email         TEXT,

    is_admin               INTEGER NOT NULL DEFAULT 0,  -- 1 = admin
    force_password_change  INTEGER NOT NULL DEFAULT 0,  -- 1 = must change on next login

    -- Reserved for future 2FA (TOTP). NULL until feature is enabled.
    totp_secret   TEXT,

    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
