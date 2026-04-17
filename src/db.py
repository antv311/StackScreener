import json
import sqlite3
from typing import Any

from screener_config import DB_PATH, DEBUG_MODE


# ── Connection ─────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _debug(msg: str) -> None:
    if DEBUG_MODE:
        print(f"[db] {msg}")


# ── Low-level helpers ──────────────────────────────────────────────────────────

def execute(sql: str, params: tuple = ()) -> int:
    """Run a write statement. Returns lastrowid."""
    with _connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        _debug(f"execute: {sql[:80]} | params={params}")
        return cur.lastrowid


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a read statement. Returns list of row dicts."""
    with _connect() as conn:
        cur = conn.execute(sql, params)
        _debug(f"query: {sql[:80]} | params={params}")
        return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Run a read statement. Returns first row or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    with _connect() as conn:
        conn.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS watchlists (
                watchlist_uid INTEGER PRIMARY KEY AUTOINCREMENT,
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
        conn.commit()
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
    cols = [c for c in data if c != "stock_uid"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    updates = ", ".join(
        f"{c} = excluded.{c}" for c in cols if c not in ("ticker", "exchange")
    )
    sql = (
        f"INSERT INTO stocks ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(ticker, exchange) DO UPDATE SET {updates}"
    )
    return execute(sql, tuple(data[c] for c in cols))


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
        """UPDATE scans
           SET status = 'complete', symbol_count = ?, scored_count = ?,
               failed_count = ?, completed_at = datetime('now'), notes = ?
           WHERE scan_uid = ?""",
        (symbol_count, scored_count, failed_count, notes, scan_uid),
    )


def fail_scan(scan_uid: int, notes: str | None = None) -> None:
    execute(
        "UPDATE scans SET status = 'failed', completed_at = datetime('now'), notes = ? WHERE scan_uid = ?",
        (notes, scan_uid),
    )


def get_scan(scan_uid: int) -> dict | None:
    return query_one("SELECT * FROM scans WHERE scan_uid = ?", (scan_uid,))


def get_recent_scans(limit: int = 10) -> list[dict]:
    return query("SELECT * FROM scans ORDER BY started_at DESC LIMIT ?", (limit,))


# ── Scan Results ───────────────────────────────────────────────────────────────

def insert_scan_result(data: dict) -> int:
    cols = [c for c in data if c != "scan_result_uid"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    return execute(
        f"INSERT INTO scan_results ({col_names}) VALUES ({placeholders})",
        tuple(data[c] for c in cols),
    )


def get_scan_results(scan_uid: int, limit: int | None = None) -> list[dict]:
    sql = """
        SELECT sr.*, s.ticker, s.exchange, s.sector, s.industry
        FROM scan_results sr
        JOIN stocks s USING (stock_uid)
        WHERE sr.scan_uid = ?
        ORDER BY sr.composite_rank ASC
    """
    if limit:
        sql += f" LIMIT {limit}"
    return query(sql, (scan_uid,))


# ── Supply Chain Events ────────────────────────────────────────────────────────

def upsert_supply_chain_event(data: dict) -> int:
    """Insert or update an event keyed on (title, region). Returns supply_chain_event_uid."""
    cols = [c for c in data if c != "supply_chain_event_uid"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    updates = ", ".join(
        f"{c} = excluded.{c}" for c in cols if c not in ("title", "region")
    )
    # Ensure the UNIQUE index exists for ON CONFLICT to fire; fall back to INSERT OR IGNORE
    # if the event already exists and only update mutable fields.
    sql = (
        f"INSERT INTO supply_chain_events ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(title, region) DO UPDATE SET {updates}, updated_at = datetime('now')"
    )
    return execute(sql, tuple(data[c] for c in cols))


def get_active_events() -> list[dict]:
    return query(
        "SELECT * FROM supply_chain_events WHERE status = 'active' ORDER BY severity DESC, detected_at DESC"
    )


def get_event(supply_chain_event_uid: int) -> dict | None:
    return query_one(
        "SELECT * FROM supply_chain_events WHERE supply_chain_event_uid = ?",
        (supply_chain_event_uid,),
    )


def resolve_event(supply_chain_event_uid: int) -> None:
    execute(
        "UPDATE supply_chain_events SET status = 'resolved', resolved_at = datetime('now'), updated_at = datetime('now') WHERE supply_chain_event_uid = ?",
        (supply_chain_event_uid,),
    )


# ── Event Stocks ───────────────────────────────────────────────────────────────

def link_event_stock(
    supply_chain_event_uid: int,
    stock_uid: int,
    role: str,
    cannot_provide: str | None = None,
    will_redirect: str | None = None,
    impact_notes: str | None = None,
    confidence: str = "medium",
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
    cols = [c for c in data if c != "calendar_event_uid"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    updates = ", ".join(
        f"{c} = excluded.{c}" for c in cols if c not in ("stock_uid", "event_type", "event_date")
    )
    sql = (
        f"INSERT INTO calendar_events ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(stock_uid, event_type, event_date) DO UPDATE SET {updates}, updated_at = datetime('now')"
    )
    return execute(sql, tuple(data[c] for c in cols))


def get_calendar_events(
    start_date: str,
    end_date: str,
    event_type: str | None = None,
) -> list[dict]:
    if event_type:
        return query(
            "SELECT * FROM calendar_events WHERE event_date BETWEEN ? AND ? AND event_type = ? ORDER BY event_date",
            (start_date, end_date, event_type),
        )
    return query(
        "SELECT * FROM calendar_events WHERE event_date BETWEEN ? AND ? ORDER BY event_date",
        (start_date, end_date),
    )


# ── Source Signals ─────────────────────────────────────────────────────────────

def upsert_source_signal(data: dict) -> int:
    cols = [c for c in data if c != "source_signal_uid"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    updates = ", ".join(
        f"{c} = excluded.{c}" for c in cols if c not in ("stock_uid", "source", "fetched_at")
    )
    sql = (
        f"INSERT INTO source_signals ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(stock_uid, source, fetched_at) DO UPDATE SET {updates}"
    )
    return execute(sql, tuple(data[c] for c in cols))


def get_stock_signals(stock_uid: int) -> list[dict]:
    return query(
        "SELECT * FROM source_signals WHERE stock_uid = ? ORDER BY fetched_at DESC",
        (stock_uid,),
    )


# ── Research Reports ───────────────────────────────────────────────────────────

def insert_research_report(data: dict) -> int:
    cols = [c for c in data if c != "research_report_uid"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    return execute(
        f"INSERT INTO research_reports ({col_names}) VALUES ({placeholders})",
        tuple(data[c] for c in cols),
    )


def get_research_reports(tag: str | None = None, limit: int = 50) -> list[dict]:
    if tag:
        return query(
            "SELECT * FROM research_reports WHERE tag = ? ORDER BY published_at DESC LIMIT ?",
            (tag, limit),
        )
    return query(
        "SELECT * FROM research_reports ORDER BY published_at DESC LIMIT ?",
        (limit,),
    )
