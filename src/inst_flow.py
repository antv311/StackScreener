"""
inst_flow.py — Congressional trade ingestion for StackScreener.

Sources (all free, no API key required):
  - Senate Stock Watcher  https://senatestockwatcher.com/api
  - House Stock Watcher   https://housestockwatcher.com/api

Trades are stored in source_signals. Purchases score CONGRESS_BUY_SCORE,
sales score CONGRESS_SELL_SCORE. Only trades newer than the last stored
signal date are ingested (incremental).

Usage:
    python src/inst_flow.py --senate
    python src/inst_flow.py --house
    python src/inst_flow.py --all
    python src/inst_flow.py --all --days 90   # only pull last N days
"""

import argparse
from datetime import datetime, timedelta, date

import requests

import db
from screener_config import (
    DEBUG_MODE,
    SENATE_WATCHER_URL,
    HOUSE_WATCHER_URL,
    CONGRESS_LOOKBACK_DAYS,
    CONGRESS_BUY_SCORE,
    CONGRESS_SELL_SCORE,
    SIGNAL_CONGRESS_BUY,
    SIGNAL_CONGRESS_SELL,
    PROVIDER_SENATE_WATCHER,
    PROVIDER_HOUSE_WATCHER,
)

_HEADERS = {"User-Agent": "StackScreener/1.0 (antv311@gmail.com)"}

# Transaction type strings returned by the APIs
_BUY_TYPES  = frozenset({"purchase", "buy", "exchange"})
_SELL_TYPES = frozenset({"sale", "sale (full)", "sale (partial)", "sell"})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cutoff_date(lookback_days: int) -> str:
    return (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")


def _signal_type(transaction_str: str) -> str | None:
    t = transaction_str.strip().lower()
    if t in _BUY_TYPES:
        return SIGNAL_CONGRESS_BUY
    if t in _SELL_TYPES:
        return SIGNAL_CONGRESS_SELL
    return None


def _sub_score(signal_type: str) -> float:
    return CONGRESS_BUY_SCORE if signal_type == SIGNAL_CONGRESS_BUY else CONGRESS_SELL_SCORE


def _already_stored(stock_uid: int, source: str, signal_url: str) -> bool:
    """Return True if this exact filing URL is already in source_signals."""
    rows = db.query(
        "SELECT 1 FROM source_signals WHERE stock_uid=? AND source=? AND signal_url=?",
        (stock_uid, source, signal_url),
    )
    return len(rows) > 0


# ── Senate ─────────────────────────────────────────────────────────────────────

def fetch_senate_trades(lookback_days: int = CONGRESS_LOOKBACK_DAYS) -> int:
    """
    Pull Senate STOCK Act disclosures and store new ones in source_signals.
    Returns count of new signals stored.
    """
    print(f"Fetching Senate trades (last {lookback_days} days)...")
    try:
        resp = requests.get(SENATE_WATCHER_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Senate API failed: {e}")
        return 0

    # API returns either a list or {"transactions": [...]}
    trades = data if isinstance(data, list) else data.get("transactions", [])
    cutoff = _cutoff_date(lookback_days)
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stored = 0

    # Cache stock lookups to avoid hitting DB per row
    stock_cache: dict[str, dict | None] = {}

    for t in trades:
        tx_date = (t.get("transaction_date") or "")[:10]
        if tx_date < cutoff:
            continue

        ticker = (t.get("ticker") or "").strip().upper()
        if not ticker or ticker == "N/A":
            continue

        if ticker not in stock_cache:
            stock_cache[ticker] = db.get_stock_by_ticker(ticker)
        stock = stock_cache[ticker]
        if not stock:
            continue

        sig_type = _signal_type(t.get("type") or t.get("transaction_type") or "")
        if not sig_type:
            continue

        senator   = t.get("senator") or t.get("first_name", "") + " " + t.get("last_name", "")
        amount    = t.get("amount") or "—"
        ptr_link  = t.get("ptr_link") or t.get("link") or ""
        reason    = f"Senator {senator.strip()} {sig_type.replace('_', ' ')} {ticker} ({amount}) on {tx_date}"

        if ptr_link and _already_stored(stock["stock_uid"], PROVIDER_SENATE_WATCHER, ptr_link):
            continue

        db.upsert_source_signal({
            "stock_uid":   stock["stock_uid"],
            "source":      PROVIDER_SENATE_WATCHER,
            "signal_type": sig_type,
            "sub_score":   _sub_score(sig_type),
            "reason_text": reason[:200],
            "signal_url":  ptr_link or None,
            "raw_data":    __import__("json").dumps(t),
            "fetched_at":  now,
        })
        stored += 1
        if DEBUG_MODE:
            print(f"  [senate] {reason}")

    print(f"  {stored} new Senate signals stored.")
    return stored


# ── House ──────────────────────────────────────────────────────────────────────

def fetch_house_trades(lookback_days: int = CONGRESS_LOOKBACK_DAYS) -> int:
    """
    Pull House STOCK Act disclosures and store new ones in source_signals.
    Returns count of new signals stored.
    """
    print(f"Fetching House trades (last {lookback_days} days)...")
    try:
        resp = requests.get(HOUSE_WATCHER_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  House API failed: {e}")
        return 0

    trades = data if isinstance(data, list) else data.get("transactions", [])
    cutoff = _cutoff_date(lookback_days)
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stored = 0
    stock_cache: dict[str, dict | None] = {}

    for t in trades:
        tx_date = (t.get("transaction_date") or "")[:10]
        if tx_date < cutoff:
            continue

        ticker = (t.get("ticker") or "").strip().upper()
        if not ticker or ticker == "N/A":
            continue

        if ticker not in stock_cache:
            stock_cache[ticker] = db.get_stock_by_ticker(ticker)
        stock = stock_cache[ticker]
        if not stock:
            continue

        sig_type = _signal_type(t.get("type") or t.get("transaction_type") or "")
        if not sig_type:
            continue

        rep      = t.get("representative") or t.get("first_name", "") + " " + t.get("last_name", "")
        amount   = t.get("amount") or "—"
        disc_url = t.get("disclosure_url") or t.get("link") or ""
        reason   = f"Rep. {rep.strip()} {sig_type.replace('_', ' ')} {ticker} ({amount}) on {tx_date}"

        if disc_url and _already_stored(stock["stock_uid"], PROVIDER_HOUSE_WATCHER, disc_url):
            continue

        db.upsert_source_signal({
            "stock_uid":   stock["stock_uid"],
            "source":      PROVIDER_HOUSE_WATCHER,
            "signal_type": sig_type,
            "sub_score":   _sub_score(sig_type),
            "reason_text": reason[:200],
            "signal_url":  disc_url or None,
            "raw_data":    __import__("json").dumps(t),
            "fetched_at":  now,
        })
        stored += 1
        if DEBUG_MODE:
            print(f"  [house] {reason}")

    print(f"  {stored} new House signals stored.")
    return stored


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener congressional trade ingestion")
    parser.add_argument("--senate", action="store_true", help="Fetch Senate STOCK Act trades")
    parser.add_argument("--house",  action="store_true", help="Fetch House STOCK Act trades")
    parser.add_argument("--all",    action="store_true", help="Fetch both Senate and House trades")
    parser.add_argument("--days",   type=int, default=CONGRESS_LOOKBACK_DAYS,
                        metavar="N", help=f"Lookback window in days (default {CONGRESS_LOOKBACK_DAYS})")
    args = parser.parse_args()

    db.init_db()

    if args.all:
        args.senate = args.house = True

    if not args.senate and not args.house:
        parser.print_help()
        return

    if args.senate:
        fetch_senate_trades(args.days)
    if args.house:
        fetch_house_trades(args.days)


if __name__ == "__main__":
    main()
