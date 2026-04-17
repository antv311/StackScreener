CREATE TABLE supply_chain_events (
    supply_chain_event_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Event Identity
    title       TEXT NOT NULL,
    region      TEXT NOT NULL,  -- 'Red Sea', 'Taiwan Strait', 'Panama Canal', etc.
    event_type  TEXT NOT NULL,  -- 'conflict', 'weather', 'labor', 'sanctions', 'accident'
    description TEXT,

    -- Severity & Status
    severity TEXT NOT NULL DEFAULT 'MEDIUM',  -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    status   TEXT NOT NULL DEFAULT 'active',  -- 'active', 'resolved', 'monitoring'

    -- Geography (for map pins)
    latitude  REAL,
    longitude REAL,

    -- Affected Supply Chain Layer
    affected_sectors    TEXT,  -- JSON array: ["Technology", "Industrials"]
    affected_industries TEXT,  -- JSON array: ["Semiconductors", "Shipping"]
    beneficiary_sectors TEXT,  -- JSON array: ["Industrials", "Energy"]

    -- Dates
    event_date  TEXT,  -- when disruption started, 'YYYY-MM-DD'
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
