CREATE TABLE watchlists (
    watchlist_uid INTEGER PRIMARY KEY AUTOINCREMENT,

    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Note: stocks are assigned to a watchlist via watchlist_uid + is_watched
-- columns embedded directly in the stocks table.
-- Simple lookup:
--   SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1
--
-- If a stock needs to appear on multiple watchlists in the future,
-- replace with a watchlist_stocks junction table using the same FK convention:
--   watchlist_uid REFERENCES watchlists(watchlist_uid)
--   stock_uid     REFERENCES stocks(stock_uid)
