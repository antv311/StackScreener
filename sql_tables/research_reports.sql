CREATE TABLE research_reports (
    research_report_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Content
    title   TEXT NOT NULL,
    summary TEXT NOT NULL,
    body    TEXT,  -- full long-form content (markdown)
    tag     TEXT NOT NULL,  -- 'supply_chain', 'fundamentals', 'inst_flow'

    -- Optional link to a specific event or stock
    supply_chain_event_uid INTEGER REFERENCES supply_chain_events(supply_chain_event_uid),
    stock_uid              INTEGER REFERENCES stocks(stock_uid),

    -- Attribution
    author     TEXT DEFAULT 'StackScreener',
    source_url TEXT,

    -- Dates
    published_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
