CREATE TABLE calendar_events (
    calendar_event_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign Key
    stock_uid INTEGER REFERENCES stocks(stock_uid),  -- nullable for macro events

    -- Event Details
    event_type TEXT NOT NULL,  -- 'earnings', 'split', 'ipo', 'economic'
    event_date TEXT NOT NULL,  -- 'YYYY-MM-DD'
    title      TEXT NOT NULL,

    -- Earnings-specific
    eps_estimate    REAL,
    eps_actual      REAL,
    revenue_estimate REAL,
    revenue_actual   REAL,
    surprise_pct    REAL,

    -- Split-specific
    split_ratio TEXT,  -- e.g. '4:1'
    split_record_date TEXT,

    -- IPO-specific
    ipo_price_low  REAL,
    ipo_price_high REAL,

    -- Economic event
    detail TEXT,  -- free text for macro events

    -- Status
    status TEXT DEFAULT 'upcoming',  -- 'upcoming', 'confirmed', 'reported'

    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
