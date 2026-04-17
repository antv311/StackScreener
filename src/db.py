import sqlite3

import crypto
from screener_config import (
    DB_PATH, DEBUG_MODE,
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
    with _connect() as conn:
        cur = conn.execute(sql, params)
        _debug(f"execute: {sql[:80]} | params={params}")
        return cur.lastrowid


def executemany(sql: str, params_list: list[tuple]) -> None:
    with _connect() as conn:
        conn.executemany(sql, params_list)
        _debug(f"executemany: {sql[:80]} | rows={len(params_list)}")


def query(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as conn:
        _debug(f"query: {sql[:80]} | params={params}")
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
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
                market_index        TEXT,
                sector              TEXT,
                industry            TEXT,
                country             TEXT,
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

                UNIQUE(ticker, exchange)
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                api_uid   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid  INTEGER NOT NULL REFERENCES users(user_uid),
                name      TEXT NOT NULL,
                api_key   TEXT NOT NULL,
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
        """)
    _debug("init_db complete")


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
    """Insert or update a stock keyed on (ticker, exchange). Returns stock_uid."""
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


# ── Scan Results ───────────────────────────────────────────────────────────────

def insert_scan_result(data: dict) -> int:
    sql, params = _build_insert_sql("scan_results", data, pk="scan_result_uid")
    return execute(sql, params)


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
    """Insert or update an event keyed on (title, region). Returns supply_chain_event_uid."""
    sql, params = _build_upsert_sql(
        "supply_chain_events", data,
        ("title", "region"),
        pk="supply_chain_event_uid",
        refresh_timestamp=True,
    )
    return execute(sql, params)


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


# ── Calendar Events ────────────────────────────────────────────────────────────

def upsert_calendar_event(data: dict) -> int:
    sql, params = _build_upsert_sql(
        "calendar_events", data,
        ("stock_uid", "event_type", "event_date"),
        pk="calendar_event_uid",
        refresh_timestamp=True,
    )
    return execute(sql, params)


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

def set_api_key(user_uid: int, name: str, plaintext_key: str) -> None:
    """Encrypt and store (or update) an API key."""
    encrypted = crypto.encrypt(plaintext_key)
    execute(
        """INSERT INTO api_keys (user_uid, name, api_key)
           VALUES (?, ?, ?)
           ON CONFLICT(user_uid, name) DO UPDATE SET
               api_key = excluded.api_key,
               updated_at = datetime('now')""",
        (user_uid, name, encrypted),
    )


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
