CREATE TABLE scan_results (
    scan_result_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign Keys
    stock_uid INTEGER NOT NULL REFERENCES stocks(stock_uid),
    scan_uid  INTEGER NOT NULL REFERENCES scans(scan_uid),

    -- Composite Score
    composite_score  REAL,
    composite_rank   INTEGER,

    -- Score Components
    score_ev_revenue    REAL,
    score_pe            REAL,
    score_ev_ebitda     REAL,
    score_profit_margin REAL,
    score_peg           REAL,
    score_debt_equity   REAL,
    score_cfo_ratio     REAL,
    score_altman_z      REAL,
    score_supply_chain  REAL,  -- additive supply chain signal layer
    score_inst_flow     REAL,  -- additive institutional flow layer

    -- Snapshot Values at Time of Scan
    price_at_scan  REAL,
    market_cap_at_scan REAL,

    scored_at TEXT NOT NULL DEFAULT (datetime('now'))
);
