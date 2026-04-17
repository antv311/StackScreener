CREATE TABLE event_stocks (
    event_stock_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign Keys
    supply_chain_event_uid INTEGER NOT NULL REFERENCES supply_chain_events(supply_chain_event_uid),
    stock_uid              INTEGER NOT NULL REFERENCES stocks(stock_uid),

    -- Role of this stock relative to the event
    role TEXT NOT NULL,  -- 'impacted' or 'beneficiary'

    -- What they can/cannot provide (populates Logistics table columns)
    cannot_provide  TEXT,  -- e.g. 'Suez Canal route (blocked)'
    will_redirect   TEXT,  -- e.g. 'Cape of Good Hope routing'
    impact_notes    TEXT,

    -- Confidence in this mapping
    confidence TEXT DEFAULT 'medium',  -- 'high', 'medium', 'low'

    linked_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(supply_chain_event_uid, stock_uid, role)
);
