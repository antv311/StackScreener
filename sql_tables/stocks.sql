CREATE TABLE stocks (
    -- Primary Identifier
    stock_uid INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Watchlist
    watchlist_uid INTEGER REFERENCES watchlists(watchlist_uid),
    is_watched    INTEGER NOT NULL DEFAULT 0,  -- 1 = on watchlist, 0 = not

    -- ==========================================
    -- 1. DESCRIPTIVE VARIABLES
    -- ==========================================
    ticker TEXT NOT NULL,
    exchange TEXT NOT NULL,
    market_index TEXT,
    sector TEXT,
    industry TEXT,
    country TEXT,
    market_cap REAL,
    dividend_yield REAL,
    float_short REAL,
    analyst_recom REAL,
    is_optionable INTEGER, -- 1 for True, 0 for False
    is_shortable INTEGER,  -- 1 for True, 0 for False
    earnings_date TEXT,    -- 'YYYY-MM-DD'
    average_volume INTEGER,
    relative_volume REAL,
    current_volume INTEGER,
    price REAL NOT NULL,
    target_price REAL,
    ipo_date TEXT,         -- 'YYYY-MM-DD'
    shares_outstanding INTEGER,
    shares_float INTEGER,

    -- ==========================================
    -- 2. FUNDAMENTAL VARIABLES
    -- ==========================================
    pe_ratio REAL,
    forward_pe REAL,
    peg_ratio REAL,
    ps_ratio REAL,
    pb_ratio REAL,
    price_to_cash REAL,
    price_to_fcf REAL,
    eps_growth_this_year REAL,
    eps_growth_next_year REAL,
    eps_growth_past_5_years REAL,
    eps_growth_next_5_years REAL,
    sales_growth_past_5_years REAL,
    eps_growth_qoq REAL,
    sales_growth_qoq REAL,
    return_on_assets REAL,
    return_on_equity REAL,
    return_on_investment REAL,
    gross_margin REAL,
    operating_margin REAL,
    net_profit_margin REAL,
    payout_ratio REAL,
    current_ratio REAL,
    quick_ratio REAL,
    lt_debt_to_equity REAL,
    total_debt_to_equity REAL,
    insider_ownership REAL,
    insider_transactions REAL,
    inst_ownership REAL,
    inst_transactions REAL,

    -- ==========================================
    -- 3. TECHNICAL VARIABLES
    -- ==========================================
    perf_today REAL,
    perf_week REAL,
    perf_month REAL,
    perf_quarter REAL,
    perf_half_year REAL,
    perf_year REAL,
    perf_ytd REAL,
    volatility_week REAL,
    volatility_month REAL,
    rsi_14 REAL,
    beta REAL,
    atr REAL,
    dist_from_sma_20 REAL,
    dist_from_sma_50 REAL,
    dist_from_sma_200 REAL,
    gap REAL,
    change_pct REAL,
    change_from_open REAL,
    dist_from_20d_high REAL,
    dist_from_20d_low REAL,
    dist_from_50d_high REAL,
    dist_from_50d_low REAL,
    dist_from_52w_high REAL,
    dist_from_52w_low REAL,
    chart_pattern TEXT,
    candlestick TEXT,

    -- ==========================================
    -- 4. MACRO SIGNAL
    -- ==========================================
    macro_signal TEXT
);