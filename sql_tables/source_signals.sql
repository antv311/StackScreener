CREATE TABLE source_signals (
    source_signal_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign Key
    stock_uid INTEGER NOT NULL REFERENCES stocks(stock_uid),

    -- Signal Source
    source TEXT NOT NULL,  -- 'quiver_quant', 'unusual_whales', 'yahoo_finance', 'motley_fool'

    -- Signal Data
    sub_score   REAL,   -- 0-100 score from this source
    reason_text TEXT,   -- human-readable explanation shown in Stock Picks card
    signal_type TEXT,   -- 'congress_buy', 'dark_pool', 'options_flow', 'analyst_rec', 'article'
    signal_url  TEXT,   -- link to original source if available

    -- Raw payload for debugging / reprocessing
    raw_data TEXT,  -- JSON blob

    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(stock_uid, source, fetched_at)
);
