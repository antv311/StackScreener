CREATE TABLE IF NOT EXISTS price_history (
    price_history_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    stock_uid INTEGER NOT NULL REFERENCES stocks(stock_uid),
    date      TEXT NOT NULL,  -- 'YYYY-MM-DD'

    -- OHLCV
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL NOT NULL,
    volume INTEGER,

    -- Corporate actions (0.0 / 1.0 when not applicable)
    dividend     REAL NOT NULL DEFAULT 0.0,  -- per-share dividend paid on this date
    split_factor REAL NOT NULL DEFAULT 1.0,  -- e.g. 4.0 for a 4:1 split; 1.0 = no split

    UNIQUE(stock_uid, date)
);
