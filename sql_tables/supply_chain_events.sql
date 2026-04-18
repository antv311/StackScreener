CREATE TABLE supply_chain_events (
    supply_chain_event_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Event Identity
    title       TEXT NOT NULL,
    region      TEXT NOT NULL,  -- 'Red Sea', 'Taiwan Strait', 'Panama Canal', etc.
    event_type  TEXT NOT NULL,  -- see EVENT_TYPE_* constants in screener_config.py
    description TEXT,

    -- Severity & Status
    severity TEXT NOT NULL DEFAULT 'MEDIUM',  -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    status   TEXT NOT NULL DEFAULT 'active',  -- 'active', 'resolved', 'monitoring'

    -- Geography (for map pins)
    latitude     REAL,
    longitude    REAL,
    country_code TEXT,  -- ISO 3166-1 alpha-2 (e.g. 'CN', 'US', 'EG')

    -- Supply Chain Classification
    trade_route         TEXT,   -- 'Red Sea', 'Taiwan Strait', 'Panama Canal', 'Strait of Hormuz'
    commodity           TEXT,   -- 'semiconductors', 'crude oil', 'grain', 'shipping containers'
    affected_sectors    TEXT,   -- JSON array: ["Technology", "Industrials"]
    affected_industries TEXT,   -- JSON array: ["Semiconductors", "Shipping"]
    beneficiary_sectors TEXT,   -- JSON array: ["Industrials", "Energy"]

    -- Source
    source_url TEXT,  -- where this event was detected / sourced from

    -- Dates
    event_date  TEXT,  -- when disruption started, 'YYYY-MM-DD'
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(title, region)
);
