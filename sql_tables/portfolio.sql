CREATE TABLE IF NOT EXISTS portfolio (
    portfolio_uid    INTEGER PRIMARY KEY AUTOINCREMENT,

    user_uid         INTEGER NOT NULL REFERENCES users(user_uid),
    stock_uid        INTEGER NOT NULL REFERENCES stocks(stock_uid),

    -- Position data (populated by Plaid or manual entry)
    quantity         REAL,
    avg_cost         REAL,
    plaid_account_id TEXT,  -- Plaid account reference for this holding

    added_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(user_uid, stock_uid)
);
