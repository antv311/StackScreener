CREATE TABLE IF NOT EXISTS edgar_facts (
    edgar_fact_uid  INTEGER PRIMARY KEY AUTOINCREMENT,

    stock_uid  INTEGER NOT NULL REFERENCES stocks(stock_uid),
    fact_type  TEXT NOT NULL,   -- 'geographic_revenue' | 'customer_concentration'
    period     TEXT NOT NULL,   -- fiscal year string, e.g. '2023'

    -- JSON blob; shape varies by fact_type:
    --   geographic_revenue:     {"US": 0.42, "China": 0.19, "Europe": 0.27, "Other": 0.12}
    --   customer_concentration: [{"name": "Apple Inc.", "pct": 0.18, "segment": "Products"}]
    value_json TEXT NOT NULL,

    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE(stock_uid, fact_type, period)
);
