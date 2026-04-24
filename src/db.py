import sqlite3

import crypto
import json

from screener_config import (
    DB_PATH, DEBUG_MODE,
    STALENESS_DAYS, HISTORY_STALENESS_DAYS,
    SCAN_STATUS_COMPLETE, SCAN_STATUS_FAILED,
    EVENT_STATUS_ACTIVE, EVENT_STATUS_RESOLVED,
    CONFIDENCE_MEDIUM, DEFAULT_AUTHOR,
)


# ── Connection ─────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _debug(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[db] {msg}")


# ── SQL builders ───────────────────────────────────────────────────────────────

def _build_upsert_sql(
    table: str,
    data: dict,
    conflict_keys: tuple[str, ...],
    pk: str | None = None,
    refresh_timestamp: bool = False,
) -> tuple[str, tuple]:
    """Generates INSERT OR REPLACE … ON CONFLICT DO UPDATE for every column except pk and conflict_keys."""
    cols = [c for c in data if c != pk]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in conflict_keys)
    if refresh_timestamp:
        updates += ", updated_at = datetime('now')"
    sql = (
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(conflict_keys)}) DO UPDATE SET {updates}"
    )
    return sql, tuple(data[c] for c in cols)


def _build_insert_sql(table: str, data: dict, pk: str | None = None) -> tuple[str, tuple]:
    cols = [c for c in data if c != pk]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    return f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", tuple(data[c] for c in cols)


# ── Low-level helpers ──────────────────────────────────────────────────────────

def execute(sql: str, params: tuple = ()) -> int:
    """Returns lastrowid, not rowcount; lastrowid is 0 on the UPDATE path of an UPSERT."""
    with _connect() as conn:
        cur = conn.execute(sql, params)
        _debug(f"execute: {sql[:80]} | params={params}")
        return cur.lastrowid


def executemany(sql: str, params_list: list[tuple]) -> None:
    with _connect() as conn:
        conn.executemany(sql, params_list)
        _debug(f"executemany: {sql[:80]} | rows={len(params_list)}")


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Always returns list[dict] — returns [] on no rows, never raises on empty result."""
    with _connect() as conn:
        _debug(f"query: {sql[:80]} | params={params}")
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Returns dict on hit, None on miss — never raises on no-match."""
    with _connect() as conn:
        _debug(f"query_one: {sql[:80]} | params={params}")
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_uid      INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                display_name  TEXT,
                email         TEXT,
                is_admin               INTEGER NOT NULL DEFAULT 0,
                force_password_change  INTEGER NOT NULL DEFAULT 0,
                totp_secret   TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS watchlists (
                watchlist_uid INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid      INTEGER REFERENCES users(user_uid),
                name          TEXT NOT NULL UNIQUE,
                description   TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS stocks (
                stock_uid     INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Watchlist
                watchlist_uid INTEGER REFERENCES watchlists(watchlist_uid),
                is_watched    INTEGER NOT NULL DEFAULT 0,

                -- Descriptive
                ticker              TEXT NOT NULL,
                exchange            TEXT NOT NULL,
                company_name        TEXT,
                market_index        TEXT,
                sector              TEXT,
                industry            TEXT,
                country             TEXT,
                business_summary    TEXT,
                market_cap          REAL,
                dividend_yield      REAL,
                float_short         REAL,
                analyst_recom       REAL,
                is_optionable       INTEGER,
                is_shortable        INTEGER,
                earnings_date       TEXT,
                average_volume      INTEGER,
                relative_volume     REAL,
                current_volume      INTEGER,
                price               REAL NOT NULL,
                target_price        REAL,
                ipo_date            TEXT,
                shares_outstanding  INTEGER,
                shares_float        INTEGER,

                -- Fundamentals
                pe_ratio                  REAL,
                forward_pe                REAL,
                peg_ratio                 REAL,
                ps_ratio                  REAL,
                pb_ratio                  REAL,
                ev_revenue                REAL,
                ev_ebitda                 REAL,
                price_to_cash             REAL,
                price_to_fcf              REAL,
                eps_growth_this_year      REAL,
                eps_growth_next_year      REAL,
                eps_growth_past_5_years   REAL,
                eps_growth_next_5_years   REAL,
                sales_growth_past_5_years REAL,
                eps_growth_qoq            REAL,
                sales_growth_qoq          REAL,
                return_on_assets          REAL,
                return_on_equity          REAL,
                return_on_investment      REAL,
                gross_margin              REAL,
                operating_margin          REAL,
                net_profit_margin         REAL,
                payout_ratio              REAL,
                current_ratio             REAL,
                quick_ratio               REAL,
                lt_debt_to_equity         REAL,
                total_debt_to_equity      REAL,
                insider_ownership         REAL,
                insider_transactions      REAL,
                inst_ownership            REAL,
                inst_transactions         REAL,

                -- Technical
                perf_today          REAL,
                perf_week           REAL,
                perf_month          REAL,
                perf_quarter        REAL,
                perf_half_year      REAL,
                perf_year           REAL,
                perf_ytd            REAL,
                volatility_week     REAL,
                volatility_month    REAL,
                rsi_14              REAL,
                beta                REAL,
                atr                 REAL,
                dist_from_sma_20    REAL,
                dist_from_sma_50    REAL,
                dist_from_sma_200   REAL,
                gap                 REAL,
                change_pct          REAL,
                change_from_open    REAL,
                dist_from_20d_high  REAL,
                dist_from_20d_low   REAL,
                dist_from_50d_high  REAL,
                dist_from_50d_low   REAL,
                dist_from_52w_high  REAL,
                dist_from_52w_low   REAL,
                chart_pattern       TEXT,
                candlestick         TEXT,

                -- Macro
                macro_signal TEXT,

                -- Enrichment tracking
                last_enriched_at TEXT,

                -- EDGAR
                cik TEXT,

                -- Status
                delisted INTEGER NOT NULL DEFAULT 0,

                UNIQUE(ticker, exchange)
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                api_uid   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid  INTEGER NOT NULL REFERENCES users(user_uid),
                name      TEXT NOT NULL,
                api_key   TEXT NOT NULL,
                url       TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_uid, name)
            );

            CREATE TABLE IF NOT EXISTS portfolio (
                portfolio_uid    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid         INTEGER NOT NULL REFERENCES users(user_uid),
                stock_uid        INTEGER NOT NULL REFERENCES stocks(stock_uid),
                quantity         REAL,
                avg_cost         REAL,
                plaid_account_id TEXT,
                added_at         TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_uid, stock_uid)
            );

            CREATE TABLE IF NOT EXISTS scans (
                scan_uid      INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_mode     TEXT NOT NULL,
                triggered_by  TEXT,
                status        TEXT NOT NULL DEFAULT 'running',
                symbol_count  INTEGER,
                scored_count  INTEGER,
                failed_count  INTEGER,
                started_at    TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at  TEXT,
                notes         TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_results (
                scan_result_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_uid        INTEGER NOT NULL REFERENCES stocks(stock_uid),
                scan_uid         INTEGER NOT NULL REFERENCES scans(scan_uid),
                composite_score  REAL,
                composite_rank   INTEGER,
                score_ev_revenue    REAL,
                score_pe            REAL,
                score_ev_ebitda     REAL,
                score_profit_margin REAL,
                score_peg           REAL,
                score_debt_equity   REAL,
                score_cfo_ratio     REAL,
                score_altman_z      REAL,
                score_supply_chain  REAL,
                score_inst_flow     REAL,
                price_at_scan       REAL,
                market_cap_at_scan  REAL,
                scored_at           TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS supply_chain_events (
                supply_chain_event_uid INTEGER PRIMARY KEY AUTOINCREMENT,
                title               TEXT NOT NULL,
                region              TEXT NOT NULL,
                event_type          TEXT NOT NULL,
                description         TEXT,
                severity            TEXT NOT NULL DEFAULT 'MEDIUM',
                status              TEXT NOT NULL DEFAULT 'active',
                latitude            REAL,
                longitude           REAL,
                affected_sectors    TEXT,
                affected_industries TEXT,
                beneficiary_sectors TEXT,
                country_code        TEXT,
                trade_route         TEXT,
                commodity           TEXT,
                source_url          TEXT,
                event_date          TEXT,
                detected_at         TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at         TEXT,
                updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(title, region)
            );

            CREATE TABLE IF NOT EXISTS event_stocks (
                event_stock_uid        INTEGER PRIMARY KEY AUTOINCREMENT,
                supply_chain_event_uid INTEGER NOT NULL REFERENCES supply_chain_events(supply_chain_event_uid),
                stock_uid              INTEGER NOT NULL REFERENCES stocks(stock_uid),
                role                   TEXT NOT NULL,
                cannot_provide         TEXT,
                will_redirect          TEXT,
                impact_notes           TEXT,
                confidence             TEXT DEFAULT 'medium',
                linked_at              TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(supply_chain_event_uid, stock_uid, role)
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                calendar_event_uid INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_uid          INTEGER REFERENCES stocks(stock_uid),
                event_type         TEXT NOT NULL,
                event_date         TEXT NOT NULL,
                title              TEXT NOT NULL,
                eps_estimate       REAL,
                eps_actual         REAL,
                revenue_estimate   REAL,
                revenue_actual     REAL,
                surprise_pct       REAL,
                split_ratio        TEXT,
                split_record_date  TEXT,
                ipo_price_low      REAL,
                ipo_price_high     REAL,
                detail             TEXT,
                status             TEXT DEFAULT 'upcoming',
                fetched_at         TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at         TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(stock_uid, event_type, event_date)
            );

            CREATE TABLE IF NOT EXISTS source_signals (
                source_signal_uid INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_uid         INTEGER NOT NULL REFERENCES stocks(stock_uid),
                source            TEXT NOT NULL,
                sub_score         REAL,
                reason_text       TEXT,
                signal_type       TEXT,
                signal_url        TEXT,
                raw_data          TEXT,
                fetched_at        TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(stock_uid, source, fetched_at)
            );

            CREATE TABLE IF NOT EXISTS research_reports (
                research_report_uid    INTEGER PRIMARY KEY AUTOINCREMENT,
                title                  TEXT NOT NULL,
                summary                TEXT NOT NULL,
                body                   TEXT,
                tag                    TEXT NOT NULL,
                supply_chain_event_uid INTEGER REFERENCES supply_chain_events(supply_chain_event_uid),
                stock_uid              INTEGER REFERENCES stocks(stock_uid),
                author                 TEXT DEFAULT 'StackScreener',
                source_url             TEXT,
                published_at           TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at             TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                setting_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid     INTEGER NOT NULL REFERENCES users(user_uid),
                key          TEXT NOT NULL,
                value        TEXT,
                updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_uid, key)
            );

            CREATE TABLE IF NOT EXISTS price_history (
                price_history_uid INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_uid         INTEGER NOT NULL REFERENCES stocks(stock_uid),
                date              TEXT NOT NULL,
                open              REAL,
                high              REAL,
                low               REAL,
                close             REAL NOT NULL,
                volume            INTEGER,
                dividend          REAL NOT NULL DEFAULT 0.0,
                split_factor      REAL NOT NULL DEFAULT 1.0,
                UNIQUE(stock_uid, date)
            );

            CREATE TABLE IF NOT EXISTS edgar_facts (
                edgar_fact_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_uid       INTEGER NOT NULL REFERENCES stocks(stock_uid),
                fact_type       TEXT NOT NULL,
                period          TEXT NOT NULL,
                value_json      TEXT NOT NULL,
                fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(stock_uid, fact_type, period)
            );

            CREATE TABLE IF NOT EXISTS news_articles (
                article_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_uid    INTEGER REFERENCES stocks(stock_uid),
                source       TEXT NOT NULL,
                headline     TEXT,
                summary      TEXT,
                body         TEXT,
                url          TEXT,
                published_at TEXT,
                sentiment    REAL,
                fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(source, url)
            );

            CREATE TABLE IF NOT EXISTS newsapi_sources (
                source_uid  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid    INTEGER NOT NULL REFERENCES users(user_uid),
                source_id   TEXT NOT NULL,
                name        TEXT NOT NULL,
                category    TEXT,
                country     TEXT,
                language    TEXT,
                enabled     INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_uid, source_id)
            );

            CREATE TABLE IF NOT EXISTS newsapi_keywords (
                keyword_uid INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid    INTEGER NOT NULL REFERENCES users(user_uid),
                keyword     TEXT NOT NULL,
                enabled     INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_uid, keyword)
            );

            CREATE TABLE IF NOT EXISTS llm_jobs (
                job_uid      INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type     TEXT NOT NULL,   -- 'classify_news' | 'extract_10k' | 'parse_8k'
                input_json   TEXT NOT NULL,   -- JSON payload for the job
                status       TEXT NOT NULL DEFAULT 'pending',  -- pending|running|done|failed
                result_json  TEXT,            -- JSON output on success
                error_text   TEXT,            -- error message on failure
                retries      INTEGER NOT NULL DEFAULT 0,
                priority     INTEGER NOT NULL DEFAULT 5,  -- 1=high … 9=low
                source_ref   TEXT,            -- e.g. 'article_uid:42' or 'cik:0001234'
                created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                started_at   TEXT,
                completed_at TEXT
            );
        """)
        _migrate_db(conn)
        _debug("init_db complete")


def _migrate_db(conn: sqlite3.Connection) -> None:
    """Add new columns to existing tables without dropping data.

    Each entry is tried once; OperationalError means the column already exists.
    """
    migrations = [
        "ALTER TABLE api_keys ADD COLUMN url TEXT",
        "ALTER TABLE api_keys ADD COLUMN display_name TEXT",
        "ALTER TABLE api_keys ADD COLUMN connector_config TEXT",
        "ALTER TABLE api_keys ADD COLUMN role TEXT",
        "ALTER TABLE supply_chain_events ADD COLUMN country_code TEXT",
        "ALTER TABLE supply_chain_events ADD COLUMN trade_route TEXT",
        "ALTER TABLE supply_chain_events ADD COLUMN commodity TEXT",
        "ALTER TABLE supply_chain_events ADD COLUMN source_url TEXT",
        "ALTER TABLE stocks ADD COLUMN delisted INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE stocks ADD COLUMN business_summary TEXT",
        "ALTER TABLE stocks ADD COLUMN cik TEXT",
        "ALTER TABLE stocks ADD COLUMN ev_revenue REAL",
        "ALTER TABLE stocks ADD COLUMN ev_ebitda REAL",
        "ALTER TABLE stocks ADD COLUMN company_name TEXT",
        "ALTER TABLE stocks ADD COLUMN ex_dividend_date TEXT",
        "ALTER TABLE stocks ADD COLUMN dividend_date TEXT",
        "ALTER TABLE stocks ADD COLUMN last_dividend_value REAL",
        "ALTER TABLE news_articles ADD COLUMN llm_classified INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE source_signals ADD COLUMN signal_url TEXT",
        "ALTER TABLE source_signals ADD COLUMN notes TEXT",
    ]
    # One-time data corrections (idempotent — safe to re-run)
    data_fixes = [
        # yfinance sometimes returns dividendYield as a percentage (6.95) instead of
        # decimal fraction (0.0695). Fix any stored values > 1.0 by dividing by 100.
        "UPDATE stocks SET dividend_yield = dividend_yield / 100 WHERE dividend_yield > 1.0",
    ]
    index_migrations = [
        "CREATE INDEX IF NOT EXISTS idx_stocks_delisted_enriched   ON stocks (delisted, last_enriched_at)",
        "CREATE INDEX IF NOT EXISTS idx_stocks_delisted_price       ON stocks (delisted, price)",
        "CREATE INDEX IF NOT EXISTS idx_edgar_facts_stock_type      ON edgar_facts (stock_uid, fact_type)",
        "CREATE INDEX IF NOT EXISTS idx_edgar_facts_type_fetched    ON edgar_facts (fact_type, fetched_at)",
        "CREATE INDEX IF NOT EXISTS idx_source_signals_stock        ON source_signals (stock_uid)",
        "CREATE INDEX IF NOT EXISTS idx_sce_status                  ON supply_chain_events (status)",
        "CREATE INDEX IF NOT EXISTS idx_scan_results_scan_rank      ON scan_results (scan_uid, composite_rank)",
        "CREATE INDEX IF NOT EXISTS idx_news_articles_source_pub    ON news_articles (source, published_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_llm_jobs_status_priority    ON llm_jobs (status, priority, created_at)",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    for sql in index_migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    for sql in data_fixes:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()


# ── Watchlists ─────────────────────────────────────────────────────────────────

def create_watchlist(name: str, description: str = "") -> int:
    return execute(
        "INSERT INTO watchlists (name, description) VALUES (?, ?)",
        (name, description),
    )


def get_watchlist(watchlist_uid: int) -> dict | None:
    return query_one("SELECT * FROM watchlists WHERE watchlist_uid = ?", (watchlist_uid,))


def get_watchlist_by_name(name: str) -> dict | None:
    return query_one("SELECT * FROM watchlists WHERE name = ?", (name,))


def get_all_watchlists() -> list[dict]:
    return query("SELECT * FROM watchlists ORDER BY name")


# ── Stocks ─────────────────────────────────────────────────────────────────────

def upsert_stock(data: dict) -> int:
    """Idempotent by (ticker, exchange); existing columns not in data are preserved via DO UPDATE SET excluded.*."""
    sql, params = _build_upsert_sql("stocks", data, ("ticker", "exchange"), pk="stock_uid")
    return execute(sql, params)


def upsert_stocks_batch(records: list[dict]) -> None:
    """Batch upsert stocks. All dicts must have identical keys."""
    if not records:
        return
    sql, _ = _build_upsert_sql("stocks", records[0], ("ticker", "exchange"), pk="stock_uid")
    params_list = [_build_upsert_sql("stocks", r, ("ticker", "exchange"), pk="stock_uid")[1] for r in records]
    executemany(sql, params_list)


def get_stock(stock_uid: int) -> dict | None:
    return query_one("SELECT * FROM stocks WHERE stock_uid = ?", (stock_uid,))


def get_stock_by_ticker(ticker: str, exchange: str | None = None) -> dict | None:
    if exchange:
        return query_one(
            "SELECT * FROM stocks WHERE ticker = ? AND exchange = ?",
            (ticker.upper(), exchange.upper()),
        )
    return query_one("SELECT * FROM stocks WHERE ticker = ?", (ticker.upper(),))


def get_watchlist_stocks(watchlist_uid: int) -> list[dict]:
    return query(
        "SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1",
        (watchlist_uid,),
    )


def add_to_watchlist(stock_uid: int, watchlist_uid: int) -> None:
    execute(
        "UPDATE stocks SET watchlist_uid = ?, is_watched = 1 WHERE stock_uid = ?",
        (watchlist_uid, stock_uid),
    )


def remove_from_watchlist(stock_uid: int) -> None:
    execute(
        "UPDATE stocks SET watchlist_uid = NULL, is_watched = 0 WHERE stock_uid = ?",
        (stock_uid,),
    )


def mark_delisted(stock_uid: int, delisted: bool = True) -> None:
    execute(
        "UPDATE stocks SET delisted = ? WHERE stock_uid = ?",
        (delisted, stock_uid),
    )


def get_active_stocks() -> list[dict]:
    """Return all non-delisted stocks."""
    return query("SELECT * FROM stocks WHERE delisted = 0 ORDER BY ticker")


def reset_enrichment_staleness(skip_delisted: bool = True) -> int:
    """Sets last_enriched_at = NULL so every stock re-qualifies; called by enricher --force before fetching pending list."""
    sql = "UPDATE stocks SET last_enriched_at = NULL"
    if skip_delisted:
        sql += " WHERE delisted = 0"
    return execute(sql)


def get_pending_enrichment(limit: int | None = None, skip_delisted: bool = True) -> list[dict]:
    """NULLS FIRST ordering ensures never-enriched stocks are processed before merely stale ones."""
    sql = """
        SELECT stock_uid, ticker, exchange FROM stocks
        WHERE (last_enriched_at IS NULL
           OR last_enriched_at < datetime('now', ?))
    """
    params: tuple = (f"-{STALENESS_DAYS} days",)
    if skip_delisted:
        sql += " AND delisted = 0"
    sql += " ORDER BY last_enriched_at ASC NULLS FIRST"
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return query(sql, params)


def get_pending_history(limit: int | None = None, skip_delisted: bool = True) -> list[dict]:
    """Filters price > 0 so pre-IPO stubs seeded with price=0.0 are never queued for history."""
    sql = """
        SELECT s.stock_uid, s.ticker, s.exchange
        FROM stocks s
        LEFT JOIN (
            SELECT stock_uid, MAX(date) AS max_date
            FROM price_history
            GROUP BY stock_uid
        ) ph ON ph.stock_uid = s.stock_uid
        WHERE s.price > 0
    """
    if skip_delisted:
        sql += " AND s.delisted = 0"
    sql += f" AND (ph.stock_uid IS NULL OR ph.max_date < date('now', ?))"
    sql += " ORDER BY s.ticker ASC"
    params: tuple = (f"-{HISTORY_STALENESS_DAYS} days",)
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return query(sql, params)


def get_sector_candidates(supply_chain_event_uid: int) -> list[dict]:
    """Return active stocks whose sector or industry matches the event's affected sectors.

    Used for Tier 1 (broad) supply chain matching. Returns stocks ordered by
    market cap descending so the most significant names surface first.
    """
    event = get_event(supply_chain_event_uid)
    if not event:
        return []
    targets = (
        json.loads(event.get("affected_sectors") or "[]")
        + json.loads(event.get("affected_industries") or "[]")
    )
    targets = list(dict.fromkeys(targets))  # deduplicate, preserve order
    if not targets:
        return []
    placeholders = ", ".join("?" * len(targets))
    return query(
        f"SELECT stock_uid, ticker, sector, industry, market_cap, business_summary "
        f"FROM stocks WHERE delisted = 0 "
        f"AND (sector IN ({placeholders}) OR industry IN ({placeholders})) "
        f"ORDER BY market_cap DESC NULLS LAST",
        tuple(targets) * 2,
    )


def ipo_checked_today() -> bool:
    """Return True if the IPO calendar was already fetched today."""
    from datetime import datetime
    row = query_one(
        "SELECT fetched_at FROM calendar_events WHERE event_type = 'ipo' ORDER BY fetched_at DESC"
    )
    if not row:
        return False
    return row["fetched_at"][:10] == datetime.now().strftime("%Y-%m-%d")


# ── Scans ──────────────────────────────────────────────────────────────────────

def create_scan(scan_mode: str, triggered_by: str = "manual") -> int:
    return execute(
        "INSERT INTO scans (scan_mode, triggered_by) VALUES (?, ?)",
        (scan_mode, triggered_by),
    )


def complete_scan(
    scan_uid: int,
    symbol_count: int,
    scored_count: int,
    failed_count: int,
    notes: str | None = None,
) -> None:
    execute(
        f"""UPDATE scans
            SET status = ?, symbol_count = ?, scored_count = ?,
                failed_count = ?, completed_at = datetime('now'), notes = ?
            WHERE scan_uid = ?""",
        (SCAN_STATUS_COMPLETE, symbol_count, scored_count, failed_count, notes, scan_uid),
    )


def fail_scan(scan_uid: int, notes: str | None = None) -> None:
    execute(
        f"UPDATE scans SET status = ?, completed_at = datetime('now'), notes = ? WHERE scan_uid = ?",
        (SCAN_STATUS_FAILED, notes, scan_uid),
    )


def get_scan(scan_uid: int) -> dict | None:
    return query_one("SELECT * FROM scans WHERE scan_uid = ?", (scan_uid,))


def get_recent_scans(limit: int = 10) -> list[dict]:
    return query("SELECT * FROM scans ORDER BY started_at DESC LIMIT ?", (limit,))


def get_heatmap_stocks(
    limit: int = 200,
    min_mcap: float | None = None,
    watchlist_only: bool = False,
) -> list[dict]:
    """Return stocks for the home heatmap, sorted by market_cap descending."""
    where = ["delisted = 0", "change_pct IS NOT NULL"]
    params: list = []
    if min_mcap is not None:
        where.append("market_cap >= ?")
        params.append(min_mcap)
    if watchlist_only:
        where.append("is_watched = 1")
    params.append(limit)
    return query(
        f"SELECT stock_uid, ticker, company_name, sector, market_cap, change_pct, price "
        f"FROM stocks WHERE {' AND '.join(where)} "
        f"ORDER BY market_cap DESC NULLS LAST LIMIT ?",
        params,
    )


# ── Scan Results ───────────────────────────────────────────────────────────────

def insert_scan_result(data: dict) -> int:
    sql, params = _build_insert_sql("scan_results", data, pk="scan_result_uid")
    return execute(sql, params)


_SCAN_RESULT_COLS = (
    "stock_uid", "scan_uid", "composite_score", "composite_rank",
    "score_ev_revenue", "score_pe", "score_ev_ebitda", "score_profit_margin",
    "score_peg", "score_debt_equity", "score_cfo_ratio", "score_altman_z",
    "score_supply_chain", "score_inst_flow", "price_at_scan", "market_cap_at_scan",
)
_SCAN_RESULT_SQL = (
    f"INSERT INTO scan_results ({', '.join(_SCAN_RESULT_COLS)}) "
    f"VALUES ({', '.join('?' * len(_SCAN_RESULT_COLS))})"
)


def insert_scan_results_batch(rows: list[dict]) -> None:
    """Insert all scan result rows in a single transaction."""
    params_list = [tuple(r.get(c) for c in _SCAN_RESULT_COLS) for r in rows]
    executemany(_SCAN_RESULT_SQL, params_list)


def get_scan_results(scan_uid: int, limit: int | None = None) -> list[dict]:
    sql = """
        SELECT sr.*, s.ticker, s.exchange, s.sector, s.industry
        FROM scan_results sr
        JOIN stocks s USING (stock_uid)
        WHERE sr.scan_uid = ?
        ORDER BY sr.composite_rank ASC
    """
    if limit:
        return query(sql + " LIMIT ?", (scan_uid, limit))
    return query(sql, (scan_uid,))


# ── Supply Chain Events ────────────────────────────────────────────────────────

def upsert_supply_chain_event(data: dict) -> int:
    """Falls back to a SELECT when lastrowid==0 because Python's sqlite3 returns 0 on the UPSERT update path."""
    sql, params = _build_upsert_sql(
        "supply_chain_events", data,
        ("title", "region"),
        pk="supply_chain_event_uid",
        refresh_timestamp=True,
    )
    uid = execute(sql, params)
    if not uid:
        # ON CONFLICT DO UPDATE path — Python's lastrowid is 0; fetch the real PK.
        row = query_one(
            "SELECT supply_chain_event_uid FROM supply_chain_events WHERE title = ? AND region = ?",
            (data["title"], data["region"]),
        )
        uid = row["supply_chain_event_uid"] if row else 0
    return uid


def get_active_events() -> list[dict]:
    return query(
        "SELECT * FROM supply_chain_events WHERE status = ? ORDER BY severity DESC, detected_at DESC",
        (EVENT_STATUS_ACTIVE,),
    )


def get_event(supply_chain_event_uid: int) -> dict | None:
    return query_one(
        "SELECT * FROM supply_chain_events WHERE supply_chain_event_uid = ?",
        (supply_chain_event_uid,),
    )


def resolve_event(supply_chain_event_uid: int) -> None:
    execute(
        "UPDATE supply_chain_events SET status = ?, resolved_at = datetime('now'), updated_at = datetime('now') WHERE supply_chain_event_uid = ?",
        (EVENT_STATUS_RESOLVED, supply_chain_event_uid),
    )


# ── Event Stocks ───────────────────────────────────────────────────────────────

def link_event_stock(
    supply_chain_event_uid: int,
    stock_uid: int,
    role: str,
    cannot_provide: str | None = None,
    will_redirect: str | None = None,
    impact_notes: str | None = None,
    confidence: str = CONFIDENCE_MEDIUM,
) -> None:
    execute(
        """INSERT INTO event_stocks
               (supply_chain_event_uid, stock_uid, role, cannot_provide, will_redirect, impact_notes, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(supply_chain_event_uid, stock_uid, role) DO UPDATE SET
               cannot_provide = excluded.cannot_provide,
               will_redirect  = excluded.will_redirect,
               impact_notes   = excluded.impact_notes,
               confidence     = excluded.confidence""",
        (supply_chain_event_uid, stock_uid, role, cannot_provide, will_redirect, impact_notes, confidence),
    )


def get_event_stocks(supply_chain_event_uid: int) -> list[dict]:
    return query(
        """SELECT es.*, s.ticker, s.exchange, s.sector
           FROM event_stocks es
           JOIN stocks s USING (stock_uid)
           WHERE es.supply_chain_event_uid = ?
           ORDER BY es.role, s.ticker""",
        (supply_chain_event_uid,),
    )


def get_stock_events(stock_uid: int) -> list[dict]:
    return query(
        """SELECT es.*, sce.title, sce.region, sce.severity, sce.status
           FROM event_stocks es
           JOIN supply_chain_events sce USING (supply_chain_event_uid)
           WHERE es.stock_uid = ?
           ORDER BY sce.detected_at DESC""",
        (stock_uid,),
    )


def get_active_event_stocks() -> list[dict]:
    """Return all event_stock links for currently active supply chain events."""
    return query(
        """SELECT es.stock_uid, es.role, es.confidence, sce.severity, sce.title
           FROM event_stocks es
           JOIN supply_chain_events sce USING (supply_chain_event_uid)
           WHERE sce.status = ?""",
        (EVENT_STATUS_ACTIVE,),
    )


def get_active_event_sectors() -> list[dict]:
    """Return sector/industry lists from all active supply chain events."""
    return query(
        """SELECT supply_chain_event_uid, affected_sectors, beneficiary_sectors,
                  affected_industries, severity
           FROM supply_chain_events WHERE status = ?""",
        (EVENT_STATUS_ACTIVE,),
    )


# ── Calendar Events ────────────────────────────────────────────────────────────

def upsert_calendar_event(data: dict) -> int:
    sql, params = _build_upsert_sql(
        "calendar_events", data,
        ("stock_uid", "event_type", "event_date"),
        pk="calendar_event_uid",
        refresh_timestamp=True,
    )
    return execute(sql, params)


def sync_dividend_calendar_events() -> int:
    """Idempotent mirror of stocks.ex_dividend_date/dividend_date into calendar_events; safe to call on every CalendarTab mount."""
    rows = query(
        "SELECT stock_uid, ticker, company_name, ex_dividend_date, dividend_date, last_dividend_value "
        "FROM stocks WHERE delisted = 0 "
        "AND (ex_dividend_date IS NOT NULL OR dividend_date IS NOT NULL)"
    )
    count = 0
    for s in rows:
        div_str = f" (${s['last_dividend_value']:.4f}/sh)" if s.get("last_dividend_value") else ""
        ticker  = s.get("ticker") or ""
        name    = s.get("company_name") or ticker
        if s.get("ex_dividend_date"):
            upsert_calendar_event({
                "stock_uid":  s["stock_uid"],
                "event_type": "ex_dividend",
                "event_date": s["ex_dividend_date"],
                "title":      f"{ticker} Ex-Div{div_str}",
                "detail":     f"Ex-dividend date — {name}",
            })
            count += 1
        if s.get("dividend_date"):
            upsert_calendar_event({
                "stock_uid":  s["stock_uid"],
                "event_type": "dividend_pay",
                "event_date": s["dividend_date"],
                "title":      f"{ticker} Div Pay{div_str}",
                "detail":     f"Dividend payment — {name}",
            })
            count += 1
    return count


def get_calendar_events_with_ticker(
    start_date: str,
    end_date: str,
    event_type: str | list[str] | None = None,
) -> list[dict]:
    """event_type accepts a list to generate an IN clause, a bare str for equality, or None for all — backward compatible."""
    sql = """
        SELECT ce.*, s.ticker, s.company_name
        FROM calendar_events ce
        LEFT JOIN stocks s USING (stock_uid)
        WHERE ce.event_date BETWEEN ? AND ?
    """
    params: tuple = (start_date, end_date)
    if isinstance(event_type, list):
        placeholders = ", ".join("?" * len(event_type))
        sql += f" AND ce.event_type IN ({placeholders})"
        params += tuple(event_type)
    elif event_type is not None:
        sql += " AND ce.event_type = ?"
        params += (event_type,)
    return query(sql + " ORDER BY ce.event_date", params)


def get_calendar_events(
    start_date: str,
    end_date: str,
    event_type: str | None = None,
) -> list[dict]:
    sql = "SELECT * FROM calendar_events WHERE event_date BETWEEN ? AND ?"
    params: tuple = (start_date, end_date)
    if event_type:
        sql += " AND event_type = ?"
        params += (event_type,)
    return query(sql + " ORDER BY event_date", params)


# ── Source Signals ─────────────────────────────────────────────────────────────

def upsert_source_signal(data: dict) -> int:
    sql, params = _build_upsert_sql(
        "source_signals", data,
        ("stock_uid", "source", "fetched_at"),
        pk="source_signal_uid",
    )
    return execute(sql, params)


def get_stock_signals(stock_uid: int) -> list[dict]:
    return query(
        "SELECT * FROM source_signals WHERE stock_uid = ? ORDER BY fetched_at DESC",
        (stock_uid,),
    )


def get_all_signal_scores() -> list[dict]:
    """Return (stock_uid, sub_score) for all signals that have a sub_score."""
    return query(
        "SELECT stock_uid, sub_score FROM source_signals WHERE sub_score IS NOT NULL"
    )


def signal_exists_by_url(source: str, signal_url: str) -> bool:
    """Return True if a signal with this source + signal_url already exists."""
    rows = query(
        "SELECT 1 FROM source_signals WHERE source = ? AND signal_url = ?",
        (source, signal_url),
    )
    return len(rows) > 0


# ── Research Reports ───────────────────────────────────────────────────────────

def insert_research_report(data: dict) -> int:
    sql, params = _build_insert_sql("research_reports", data, pk="research_report_uid")
    return execute(sql, params)


def get_research_reports(tag: str | None = None, limit: int = 50) -> list[dict]:
    sql = "SELECT * FROM research_reports"
    params: tuple = ()
    if tag:
        sql += " WHERE tag = ?"
        params = (tag,)
    return query(sql + " ORDER BY published_at DESC LIMIT ?", params + (limit,))


# ── Users ──────────────────────────────────────────────────────────────────────

def create_user(
    username: str,
    password: str,
    display_name: str = "",
    email: str = "",
    is_admin: bool = False,
    force_password_change: bool = False,
) -> int:
    password_hash, salt = crypto.hash_password(password)
    return execute(
        """INSERT INTO users
               (username, password_hash, salt, display_name, email, is_admin, force_password_change)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (username, password_hash, salt, display_name, email, int(is_admin), int(force_password_change)),
    )


def get_user(user_uid: int) -> dict | None:
    return query_one("SELECT * FROM users WHERE user_uid = ?", (user_uid,))


def get_user_by_username(username: str) -> dict | None:
    return query_one("SELECT * FROM users WHERE username = ?", (username,))


def verify_user_password(username: str, password: str) -> dict | None:
    """Return the user dict if credentials are valid, else None."""
    user = get_user_by_username(username)
    if user and crypto.verify_password(password, user["password_hash"], user["salt"]):
        return user
    return None


def update_password(user_uid: int, new_password: str) -> None:
    password_hash, salt = crypto.hash_password(new_password)
    execute(
        """UPDATE users
           SET password_hash = ?, salt = ?, force_password_change = 0, updated_at = datetime('now')
           WHERE user_uid = ?""",
        (password_hash, salt, user_uid),
    )


def seed_default_user() -> None:
    """Create the default admin user if no users exist."""
    if query_one("SELECT 1 FROM users LIMIT 1"):
        return
    create_user(
        username="admin",
        password="admin",
        display_name="Administrator",
        is_admin=True,
        force_password_change=True,
    )
    _debug("seed_default_user: created admin")


# ── API Keys ───────────────────────────────────────────────────────────────────

def set_api_key(
    user_uid: int,
    name: str,
    plaintext_key: str,
    url: str | None = None,
    display_name: str | None = None,
    role: str | None = None,
) -> None:
    """Encrypt and store (or update) an API key.

    `name`  — unique human label (e.g. "TheNewsAPI Free", "aisstream").
    `role`  — functional category for multi-provider lookup (e.g. "news_connector").
              Defaults to name when omitted (preserves existing 1:1 system key behaviour).
    """
    encrypted   = crypto.encrypt(plaintext_key)
    stored_role = role if role is not None else name
    execute(
        """INSERT INTO api_keys (user_uid, name, api_key, url, display_name, role)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_uid, name) DO UPDATE SET
               api_key      = excluded.api_key,
               url          = excluded.url,
               display_name = COALESCE(excluded.display_name, display_name),
               role         = COALESCE(excluded.role, role),
               updated_at   = datetime('now')""",
        (user_uid, name, encrypted, url, display_name, stored_role),
    )


def get_api_keys_by_role(user_uid: int, role: str) -> list[dict]:
    """Return all api_keys rows for a given role (decrypted key included)."""
    rows = query(
        "SELECT * FROM api_keys WHERE user_uid = ? AND role = ? ORDER BY name",
        (user_uid, role),
    )
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["api_key_plain"] = crypto.decrypt(d["api_key"]) if d.get("api_key") else None
        except Exception:
            d["api_key_plain"] = None
        result.append(d)
    return result


def get_api_key(user_uid: int, name: str) -> str | None:
    """Return decrypted API key, or None if not set."""
    row = query_one(
        "SELECT api_key FROM api_keys WHERE user_uid = ? AND name = ?",
        (user_uid, name),
    )
    if row is None:
        return None
    return crypto.decrypt(row["api_key"])


def list_api_keys(user_uid: int) -> list[str]:
    """Return provider names that have a key stored for this user."""
    rows = query("SELECT name FROM api_keys WHERE user_uid = ? ORDER BY name", (user_uid,))
    return [r["name"] for r in rows]


def delete_api_key(user_uid: int, name: str) -> None:
    execute("DELETE FROM api_keys WHERE user_uid = ? AND name = ?", (user_uid, name))


def set_connector_config(user_uid: int, name: str, config_json: str) -> None:
    """Store or update the connector config JSON for an api_keys row."""
    execute(
        "UPDATE api_keys SET connector_config = ? WHERE user_uid = ? AND name = ?",
        (config_json, user_uid, name),
    )


def get_connector_config(user_uid: int, name: str) -> dict | None:
    """Return the parsed connector config dict from api_keys, or None if not configured."""
    import json as _json
    row = query_one(
        "SELECT connector_config FROM api_keys WHERE user_uid = ? AND name = ?",
        (user_uid, name),
    )
    if row is None or not row["connector_config"]:
        return None
    try:
        return _json.loads(row["connector_config"])
    except Exception:
        return None


# ── NewsAPI source and keyword configuration ────────────────────────────────────

def upsert_newsapi_sources(user_uid: int, sources: list[dict]) -> int:
    """Upsert a batch of source dicts from the /v2/sources API response. Returns count."""
    for s in sources:
        execute(
            """INSERT INTO newsapi_sources (user_uid, source_id, name, category, country, language)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_uid, source_id) DO UPDATE SET
                   name     = excluded.name,
                   category = excluded.category,
                   country  = excluded.country,
                   language = excluded.language""",
            (user_uid, s["id"], s["name"], s.get("category"), s.get("country"), s.get("language")),
        )
    return len(sources)


def get_newsapi_sources(user_uid: int, enabled_only: bool = False) -> list[dict]:
    sql    = "SELECT * FROM newsapi_sources WHERE user_uid = ?"
    params: tuple = (user_uid,)
    if enabled_only:
        sql += " AND enabled = 1"
    sql += " ORDER BY category, name"
    return query(sql, params)


def toggle_newsapi_source(user_uid: int, source_id: str, enabled: bool) -> None:
    execute(
        "UPDATE newsapi_sources SET enabled = ? WHERE user_uid = ? AND source_id = ?",
        (1 if enabled else 0, user_uid, source_id),
    )


def get_newsapi_keywords(user_uid: int) -> list[dict]:
    return query(
        "SELECT * FROM newsapi_keywords WHERE user_uid = ? ORDER BY created_at",
        (user_uid,),
    )


def add_newsapi_keyword(user_uid: int, keyword: str) -> int:
    return execute(
        """INSERT INTO newsapi_keywords (user_uid, keyword)
           VALUES (?, ?)
           ON CONFLICT(user_uid, keyword) DO UPDATE SET enabled = 1""",
        (user_uid, keyword.strip()),
    )


def delete_newsapi_keyword(user_uid: int, keyword_uid: int) -> None:
    execute(
        "DELETE FROM newsapi_keywords WHERE keyword_uid = ? AND user_uid = ?",
        (keyword_uid, user_uid),
    )


def toggle_newsapi_keyword(user_uid: int, keyword_uid: int, enabled: bool) -> None:
    execute(
        "UPDATE newsapi_keywords SET enabled = ? WHERE keyword_uid = ? AND user_uid = ?",
        (1 if enabled else 0, keyword_uid, user_uid),
    )


# ── Portfolio ──────────────────────────────────────────────────────────────────

def upsert_portfolio_position(
    user_uid: int,
    stock_uid: int,
    quantity: float | None = None,
    avg_cost: float | None = None,
    plaid_account_id: str | None = None,
) -> None:
    execute(
        """INSERT INTO portfolio (user_uid, stock_uid, quantity, avg_cost, plaid_account_id)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_uid, stock_uid) DO UPDATE SET
               quantity         = excluded.quantity,
               avg_cost         = excluded.avg_cost,
               plaid_account_id = excluded.plaid_account_id,
               updated_at       = datetime('now')""",
        (user_uid, stock_uid, quantity, avg_cost, plaid_account_id),
    )


def get_portfolio(user_uid: int) -> list[dict]:
    return query(
        """SELECT p.*, s.ticker, s.exchange, s.sector, s.price
           FROM portfolio p
           JOIN stocks s USING (stock_uid)
           WHERE p.user_uid = ?
           ORDER BY s.ticker""",
        (user_uid,),
    )


def remove_portfolio_position(user_uid: int, stock_uid: int) -> None:
    execute(
        "DELETE FROM portfolio WHERE user_uid = ? AND stock_uid = ?",
        (user_uid, stock_uid),
    )


# ── EDGAR Facts ───────────────────────────────────────────────────────────────

def upsert_edgar_fact(data: dict) -> int:
    """Insert or update an EDGAR fact keyed on (stock_uid, fact_type, period)."""
    if "fetched_at" not in data:
        from datetime import datetime as _dt
        data = {**data, "fetched_at": _dt.now().strftime("%Y-%m-%d %H:%M:%S")}
    sql, params = _build_upsert_sql(
        "edgar_facts", data,
        ("stock_uid", "fact_type", "period"),
        pk="edgar_fact_uid",
        refresh_timestamp=False,
    )
    return execute(sql, params)


def get_edgar_facts(stock_uid: int, fact_type: str) -> list[dict]:
    return query(
        "SELECT * FROM edgar_facts WHERE stock_uid = ? AND fact_type = ? ORDER BY period DESC",
        (stock_uid, fact_type),
    )


def get_stocks_by_china_exposure(min_pct: float = 0.10) -> list[dict]:
    """Return stocks whose most recent geographic_revenue fact shows China >= min_pct."""
    return query(
        """
        SELECT s.stock_uid, s.ticker, s.sector, s.market_cap,
               ef.value_json, ef.period
        FROM stocks s
        JOIN edgar_facts ef ON ef.stock_uid = s.stock_uid
        WHERE s.delisted = 0
          AND ef.fact_type = 'geographic_revenue'
          AND ef.period = (
              SELECT MAX(ef2.period) FROM edgar_facts ef2
              WHERE ef2.stock_uid = s.stock_uid AND ef2.fact_type = 'geographic_revenue'
          )
          AND CAST(json_extract(ef.value_json, '$.China') AS REAL) >= ?
        ORDER BY json_extract(ef.value_json, '$.China') DESC
        """,
        (min_pct,),
    )


def get_active_china_events() -> list[dict]:
    """Return active supply chain events that are China- or Taiwan-related."""
    return query(
        """
        SELECT supply_chain_event_uid, title, region, severity
        FROM supply_chain_events
        WHERE status = 'active'
          AND (country_code = 'CN'
               OR region LIKE '%China%'
               OR region LIKE '%Taiwan%')
        """
    )


def get_china_revenue_map() -> dict[int, float]:
    """Return {stock_uid: china_pct} for all stocks with EDGAR geographic data.

    Uses the most recent period. Only includes stocks where China revenue > 0.
    """
    rows = query(
        """
        SELECT ef.stock_uid,
               CAST(json_extract(ef.value_json, '$.China') AS REAL) AS china_pct
        FROM edgar_facts ef
        WHERE ef.fact_type = 'geographic_revenue'
          AND ef.period = (
              SELECT MAX(ef2.period) FROM edgar_facts ef2
              WHERE ef2.stock_uid = ef.stock_uid
                AND ef2.fact_type = 'geographic_revenue'
          )
          AND CAST(json_extract(ef.value_json, '$.China') AS REAL) > 0
        """
    )
    return {r["stock_uid"]: float(r["china_pct"]) for r in rows}


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(user_uid: int, key: str, default: str | None = None) -> str | None:
    row = query_one(
        "SELECT value FROM settings WHERE user_uid = ? AND key = ?",
        (user_uid, key),
    )
    return row["value"] if row else default


def set_setting(user_uid: int, key: str, value: str) -> None:
    execute(
        """INSERT INTO settings (user_uid, key, value) VALUES (?, ?, ?)
           ON CONFLICT(user_uid, key) DO UPDATE SET
               value = excluded.value, updated_at = datetime('now')""",
        (user_uid, key, value),
    )


def get_all_settings(user_uid: int) -> dict[str, str | None]:
    rows = query("SELECT key, value FROM settings WHERE user_uid = ?", (user_uid,))
    return {r["key"]: r["value"] for r in rows}


# ── Price History ──────────────────────────────────────────────────────────────

def upsert_price_history_batch(records: list[dict]) -> None:
    """Batch upsert OHLCV + dividend rows. All dicts must have identical keys."""
    if not records:
        return
    sql, _ = _build_upsert_sql("price_history", records[0], ("stock_uid", "date"), pk="price_history_uid")
    params_list = [
        _build_upsert_sql("price_history", r, ("stock_uid", "date"), pk="price_history_uid")[1]
        for r in records
    ]
    executemany(sql, params_list)


def get_price_history(
    stock_uid: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    sql = "SELECT * FROM price_history WHERE stock_uid = ?"
    params: tuple = (stock_uid,)
    if start_date:
        sql += " AND date >= ?"
        params += (start_date,)
    if end_date:
        sql += " AND date <= ?"
        params += (end_date,)
    return query(sql + " ORDER BY date ASC", params)


def get_dividend_history(stock_uid: int) -> list[dict]:
    """Return only rows where a dividend was paid."""
    return query(
        "SELECT date, dividend FROM price_history WHERE stock_uid = ? AND dividend > 0 ORDER BY date ASC",
        (stock_uid,),
    )


# ── News Articles ──────────────────────────────────────────────────────────────

def upsert_news_article(data: dict) -> int:
    """Insert or update a news article keyed on (source, url). Returns article_uid."""
    sql, params = _build_upsert_sql(
        "news_articles", data,
        ("source", "url"),
        pk="article_uid",
    )
    return execute(sql, params)


def get_news_articles(source: str | None = None, limit: int = 50) -> list[dict]:
    sql = """
        SELECT na.*, s.ticker
        FROM news_articles na
        LEFT JOIN stocks s ON s.stock_uid = na.stock_uid
    """
    params: tuple = ()
    if source is not None:
        sql += " WHERE na.source = ?"
        params = (source,)
    return query(sql + " ORDER BY na.published_at DESC LIMIT ?", params + (limit,))


def get_news_articles_for_stock(stock_uid: int, limit: int = 20) -> list[dict]:
    return query(
        "SELECT * FROM news_articles WHERE stock_uid = ? ORDER BY published_at DESC LIMIT ?",
        (stock_uid, limit),
    )


def get_unclassified_news_articles(limit: int = 50) -> list[dict]:
    """Return articles not yet passed through the LLM classifier, oldest first."""
    return query(
        "SELECT * FROM news_articles WHERE llm_classified = 0 ORDER BY published_at ASC LIMIT ?",
        (limit,),
    )


def mark_article_classified(article_uid: int) -> None:
    execute(
        "UPDATE news_articles SET llm_classified = 1 WHERE article_uid = ?",
        (article_uid,),
    )


# ── LLM Job Queue ──────────────────────────────────────────────────────────────

def enqueue_llm_job(
    job_type: str,
    input_json: str,
    source_ref: str | None = None,
    priority: int = 5,
) -> int:
    return execute(
        "INSERT INTO llm_jobs (job_type, input_json, source_ref, priority) VALUES (?, ?, ?, ?)",
        (job_type, input_json, source_ref, priority),
    )


def dequeue_next_llm_job() -> dict | None:
    """Atomic UPDATE→SELECT prevents two workers from claiming the same job on concurrent calls."""
    with _connect() as conn:
        conn.execute("""
            UPDATE llm_jobs
            SET status = 'running', started_at = datetime('now')
            WHERE job_uid = (
                SELECT job_uid FROM llm_jobs
                WHERE status = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            )
        """)
        conn.commit()
        return conn.execute(
            "SELECT * FROM llm_jobs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()


def complete_llm_job(job_uid: int, result_json: str) -> None:
    execute(
        "UPDATE llm_jobs SET status = 'done', result_json = ?, completed_at = datetime('now') WHERE job_uid = ?",
        (result_json, job_uid),
    )


def fail_llm_job(job_uid: int, error_text: str, max_retries: int = 3) -> None:
    """Increments retries and re-queues as 'pending' until max_retries is reached, then promotes to 'failed'."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT retries FROM llm_jobs WHERE job_uid = ?", (job_uid,)
        ).fetchone()
        if not row:
            return
        new_retries = row["retries"] + 1
        new_status  = "failed" if new_retries >= max_retries else "pending"
        conn.execute(
            "UPDATE llm_jobs SET status = ?, retries = ?, error_text = ? WHERE job_uid = ?",
            (new_status, new_retries, error_text, job_uid),
        )
        conn.commit()


def get_llm_queue_stats() -> dict:
    rows = query("SELECT status, COUNT(*) AS cnt FROM llm_jobs GROUP BY status")
    return {r["status"]: r["cnt"] for r in rows}


def get_llm_jobs(status: str | None = None, limit: int = 50) -> list[dict]:
    if status is not None:
        return query(
            "SELECT * FROM llm_jobs WHERE status = ? ORDER BY priority ASC, created_at ASC LIMIT ?",
            (status, limit),
        )
    return query("SELECT * FROM llm_jobs ORDER BY priority ASC, created_at ASC LIMIT ?", (limit,))


def get_distinct_job_types() -> list[str]:
    """Return all job_type values that currently have queued (pending/paused) jobs."""
    rows = query(
        "SELECT DISTINCT job_type FROM llm_jobs WHERE status IN ('pending','paused','running') ORDER BY job_type"
    )
    return [r["job_type"] for r in rows]


def pause_llm_jobs(job_type: str | None = None) -> int:
    """Moves pending→paused; the LLM worker skips paused jobs so work halts without losing queue position."""
    if job_type:
        return execute(
            "UPDATE llm_jobs SET status = 'paused' WHERE status = 'pending' AND job_type = ?",
            (job_type,),
        )
    return execute("UPDATE llm_jobs SET status = 'paused' WHERE status = 'pending'")


def resume_llm_jobs(job_type: str | None = None) -> int:
    """Move paused → pending. Returns affected row count."""
    if job_type:
        return execute(
            "UPDATE llm_jobs SET status = 'pending' WHERE status = 'paused' AND job_type = ?",
            (job_type,),
        )
    return execute("UPDATE llm_jobs SET status = 'pending' WHERE status = 'paused'")


def cancel_llm_jobs(job_type: str | None = None) -> int:
    """Moves pending/paused→cancelled; irreversible — cancelled jobs are never retried or resumed."""
    if job_type:
        return execute(
            "UPDATE llm_jobs SET status = 'cancelled' WHERE status IN ('pending','paused') AND job_type = ?",
            (job_type,),
        )
    return execute(
        "UPDATE llm_jobs SET status = 'cancelled' WHERE status IN ('pending','paused')"
    )


def set_job_priority(job_type: str, priority: int) -> int:
    """Bulk-set priority for all pending/paused jobs of a given type (1=highest, 9=lowest)."""
    return execute(
        "UPDATE llm_jobs SET priority = ? WHERE status IN ('pending','paused') AND job_type = ?",
        (max(1, min(9, priority)), job_type),
    )


# ── DB Browser (db_app.py) ─────────────────────────────────────────────────────

def get_table_names() -> list[str]:
    rows = query(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    )
    return [r["name"] for r in rows]


def browse_table(table: str, limit: int = 100, offset: int = 0) -> list[dict]:
    allowed = {r["name"] for r in query("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if table not in allowed:
        raise ValueError(f"Unknown table: {table!r}")
    return query(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset))


def execute_raw_sql(sql: str, params: tuple = ()) -> list[dict]:
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are permitted.")
    return query(sql, params)


def get_all_tickers() -> frozenset[str]:
    """Return all active ticker symbols as a frozenset — used for mention detection."""
    rows = query("SELECT ticker FROM stocks WHERE delisted = 0")
    return frozenset(r["ticker"] for r in rows)


def get_watched_tickers() -> list[str]:
    """Return tickers for all stocks currently on a watchlist."""
    rows = query(
        "SELECT ticker FROM stocks WHERE is_watched = 1 AND delisted = 0 ORDER BY ticker"
    )
    return [r["ticker"] for r in rows]


def get_stocks_by_tickers(tickers: list[str]) -> dict[str, dict]:
    """Return {ticker: stock} for all given tickers present in the DB."""
    if not tickers:
        return {}
    placeholders = ", ".join("?" * len(tickers))
    rows = query(
        f"SELECT * FROM stocks WHERE ticker IN ({placeholders}) AND delisted = 0",
        tuple(tickers),
    )
    return {r["ticker"]: r for r in rows}


def get_news_article_urls(source: str) -> set[str]:
    """Return set of all stored URLs for a given news source — used for deduplication."""
    rows = query(
        "SELECT url FROM news_articles WHERE source = ? AND url IS NOT NULL",
        (source,),
    )
    return {r["url"] for r in rows}


def get_active_stock_count() -> int:
    """Return count of non-delisted stocks."""
    row = query_one("SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0")
    return row["n"] if row else 0


def get_enriched_stock_count() -> int:
    """Return count of non-delisted stocks that have been enriched at least once."""
    row = query_one(
        "SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0 AND last_enriched_at IS NOT NULL"
    )
    return row["n"] if row else 0
