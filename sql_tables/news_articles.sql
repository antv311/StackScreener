-- news_articles: headlines, full transcripts, and article text from all news sources.
-- One row per article/episode. Ticker mentions create rows in source_signals.
CREATE TABLE IF NOT EXISTS news_articles (
    article_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_uid    INTEGER REFERENCES stocks(stock_uid),  -- primary ticker, nullable
    source       TEXT NOT NULL,                          -- see NEWS_SOURCE_* in screener_config.py
    headline     TEXT,
    summary      TEXT,
    body         TEXT,                                   -- full transcript or article text
    url          TEXT,                                   -- audio URL, article URL, or PDF path
    published_at TEXT,
    sentiment    REAL,                                   -- NULL until sentiment scoring added (Phase 2d+)
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, url)
);
