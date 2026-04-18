"""
enricher.py — Background worker that fills in full fundamentals for seeded stocks.

Reads stocks with NULL or stale fundamentals and enriches them via yfinance,
one at a time with configurable rate limiting. Safe to kill and restart —
progress is committed after each stock.

Also runs a daily IPO calendar check (Yahoo Finance calendar API) to pick up
upcoming listings that won't appear in the NYSE/NASDAQ screener yet.

Usage:
    python enricher.py              # run until all stocks are up to date
    python enricher.py --rate 0.5   # seconds between requests (default 0.5)
    python enricher.py --limit 100  # process at most 100 stocks then exit
    python enricher.py --ipo-only   # only run the IPO calendar check, then exit
"""

import argparse
import queue
import threading
import time
from datetime import datetime, timedelta

import yfinance as yf

import db
from screener_config import DEBUG_MODE, STALENESS_DAYS

_EXCHANGE_NORM: dict[str, str] = {
    "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ",
    "NYQ": "NYSE",   "NYE": "NYSE",
    "PCX": "NYSE ARCA",
}


def _norm_exchange(raw: str | None) -> str | None:
    if not raw:
        return None
    return _EXCHANGE_NORM.get(raw.upper(), raw.upper())


def _ts_to_date(ts) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(str(ts))).strftime("%Y-%m-%d")
    except Exception:
        return None


def _map_info(ticker: str, exchange: str, info: dict) -> dict:
    """Map a yfinance .info dict to our stocks schema columns."""
    return {
        "ticker":               ticker.upper(),
        "exchange":             _norm_exchange(info.get("exchange")) or exchange,
        "sector":               info.get("sector"),
        "industry":             info.get("industry"),
        "country":              info.get("country"),
        "market_cap":           info.get("marketCap"),
        "dividend_yield":       info.get("dividendYield"),
        "float_short":          info.get("shortPercentOfFloat"),
        "analyst_recom":        info.get("recommendationMean"),
        "earnings_date":        _ts_to_date(info.get("earningsTimestamp")),
        "average_volume":       info.get("averageVolume"),
        "current_volume":       info.get("regularMarketVolume"),
        "price":                info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
        "target_price":         info.get("targetMeanPrice"),
        "shares_outstanding":   info.get("sharesOutstanding"),
        "shares_float":         info.get("floatShares"),
        "pe_ratio":             info.get("trailingPE"),
        "forward_pe":           info.get("forwardPE"),
        "peg_ratio":            info.get("trailingPegRatio"),
        "ps_ratio":             info.get("priceToSalesTrailing12Months"),
        "pb_ratio":             info.get("priceToBook"),
        "return_on_assets":     info.get("returnOnAssets"),
        "return_on_equity":     info.get("returnOnEquity"),
        "gross_margin":         info.get("grossMargins"),
        "operating_margin":     info.get("operatingMargins"),
        "net_profit_margin":    info.get("profitMargins"),
        "payout_ratio":         info.get("payoutRatio"),
        "current_ratio":        info.get("currentRatio"),
        "quick_ratio":          info.get("quickRatio"),
        "total_debt_to_equity": info.get("debtToEquity"),
        "insider_ownership":    info.get("heldPercentInsiders"),
        "inst_ownership":       info.get("heldPercentInstitutions"),
        "beta":                 info.get("beta"),
        "last_enriched_at":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _get_pending(limit: int | None) -> list[dict]:
    """Return stocks that need enrichment: never enriched or data is stale."""
    sql = """
        SELECT stock_uid, ticker, exchange FROM stocks
        WHERE last_enriched_at IS NULL
           OR last_enriched_at < datetime('now', ?)
        ORDER BY last_enriched_at ASC NULLS FIRST
    """
    params: tuple = (f"-{STALENESS_DAYS} days",)
    if limit:
        sql += " LIMIT ?"
        params += (limit,)
    return db.query(sql, params)


def _enrich_one(stock: dict) -> bool:
    ticker = stock["ticker"]
    try:
        info = yf.Ticker(ticker).info
        if not info or (not info.get("currentPrice") and not info.get("regularMarketPrice")):
            if DEBUG_MODE:
                print(f"[enricher] {ticker}: empty response, skipping")
            return False
        db.upsert_stock(_map_info(ticker, stock["exchange"], info))
        return True
    except Exception as e:
        print(f"  XX {ticker}: {e}")
        return False


def _worker(
    work_queue: queue.Queue,
    rate_limit: float,
    stats: dict,
    lock: threading.Lock,
) -> None:
    while True:
        try:
            stock = work_queue.get(timeout=2)
        except queue.Empty:
            break

        success = _enrich_one(stock)
        time.sleep(rate_limit)

        with lock:
            if success:
                stats["ok"] += 1
            else:
                stats["failed"] += 1
            done = stats["ok"] + stats["failed"]
            status = "OK" if success else "XX"
            print(f"  {status} [{done}/{stats['total']}] {stock['ticker']}")

        work_queue.task_done()


# ── IPO calendar ──────────────────────────────────────────────────────────────

_IPO_LOOKAHEAD_DAYS = 90


def _ipo_checked_today() -> bool:
    """Return True if the IPO calendar was already fetched today."""
    row = db.query_one(
        "SELECT fetched_at FROM calendar_events WHERE event_type = 'ipo' ORDER BY fetched_at DESC"
    )
    if not row:
        return False
    return row["fetched_at"][:10] == datetime.now().strftime("%Y-%m-%d")


def _fetch_ipo_calendar():
    today = datetime.now()
    end   = today + timedelta(days=_IPO_LOOKAHEAD_DAYS)
    return yf.Calendars().get_ipo_info_calendar(
        today.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
    )


def check_upcoming_ipos() -> None:
    """Fetch upcoming IPOs via yfinance and store in calendar_events.

    Runs at most once per day. Pre-seeds stocks table for any IPO that already
    has a ticker symbol so it can be watched before it lists.
    """
    if _ipo_checked_today():
        if DEBUG_MODE:
            print("[enricher] IPO calendar already checked today, skipping")
        return

    print("Checking IPO calendar...")
    try:
        df = _fetch_ipo_calendar()
    except Exception as e:
        print(f"  IPO calendar fetch failed: {e}")
        return

    if df is None or df.empty:
        print("  No upcoming IPOs found.")
        return

    seeded = 0
    stored = 0
    for ticker, row in df.iterrows():
        ticker = str(ticker).strip().upper().replace(".", "-") if ticker else None
        name       = row.get("Company") or ticker or "Unknown"
        exchange   = row.get("Exchange") or ""
        date_val   = row.get("Date")
        ipo_date   = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else None
        price_low  = row.get("Price From") if not _is_nan(row.get("Price From")) else None
        price_high = row.get("Price To")   if not _is_nan(row.get("Price To"))   else None

        if ticker:
            db.upsert_stock({
                "ticker":   ticker,
                "exchange": _norm_exchange(exchange) or exchange or "UNKNOWN",
                "price":    0.0,
                "ipo_date": ipo_date,
            })
            seeded += 1

        existing = db.get_stock_by_ticker(ticker) if ticker else None
        db.upsert_calendar_event({
            "stock_uid":      existing["stock_uid"] if existing else None,
            "event_type":     "ipo",
            "event_date":     ipo_date or datetime.now().strftime("%Y-%m-%d"),
            "title":          f"{name} IPO",
            "ipo_price_low":  price_low,
            "ipo_price_high": price_high,
            "status":         "upcoming",
        })
        stored += 1

    print(f"  {stored} upcoming IPOs stored, {seeded} pre-seeded in stocks.")


def _is_nan(val) -> bool:
    try:
        import math
        return val is None or math.isnan(float(val))
    except (TypeError, ValueError):
        return False


def run(
    rate_limit: float = 0.5,
    num_workers: int = 1,
    limit: int | None = None,
    ipo_only: bool = False,
    history_only: bool = False,
    history_period: str = "5y",
) -> None:
    check_upcoming_ipos()

    if ipo_only:
        return

    if history_only:
        _run_history(rate_limit, num_workers, limit, history_period)
        return

    pending = _get_pending(limit)
    if not pending:
        print("All stocks are up to date.")
        return

    print(f"Enriching {len(pending)} stocks  |  rate: {rate_limit}s/request  |  workers: {num_workers}")

    work_queue: queue.Queue = queue.Queue()
    for stock in pending:
        work_queue.put(stock)

    stats = {"ok": 0, "failed": 0, "total": len(pending)}
    lock = threading.Lock()

    threads = [
        threading.Thread(target=_worker, args=(work_queue, rate_limit, stats, lock), daemon=True)
        for _ in range(num_workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nDone - {stats['ok']} enriched, {stats['failed']} failed.")


# ── Price history ──────────────────────────────────────────────────────────────

_HISTORY_STALENESS_DAYS = 3  # accounts for weekends + holidays


def _get_pending_history(limit: int | None) -> list[dict]:
    """Return listed stocks whose price history is missing or stale."""
    sql = """
        SELECT s.stock_uid, s.ticker, s.exchange
        FROM stocks s
        WHERE s.price > 0
          AND (
              NOT EXISTS (
                  SELECT 1 FROM price_history ph WHERE ph.stock_uid = s.stock_uid
              )
              OR (
                  SELECT MAX(ph.date) FROM price_history ph WHERE ph.stock_uid = s.stock_uid
              ) < date('now', ?)
          )
        ORDER BY s.ticker ASC
    """
    params: tuple = (f"-{_HISTORY_STALENESS_DAYS} days",)
    if limit:
        sql += " LIMIT ?"
        params += (limit,)
    return db.query(sql, params)


def _map_history_row(stock_uid: int, ts, row) -> dict:
    splits = float(row.get("Stock Splits", 0) or 0)
    return {
        "stock_uid":    stock_uid,
        "date":         ts.strftime("%Y-%m-%d"),
        "open":         round(float(row["Open"]),   4) if not _is_nan(row.get("Open"))   else None,
        "high":         round(float(row["High"]),   4) if not _is_nan(row.get("High"))   else None,
        "low":          round(float(row["Low"]),    4) if not _is_nan(row.get("Low"))    else None,
        "close":        round(float(row["Close"]),  4),
        "volume":       int(row["Volume"])               if not _is_nan(row.get("Volume")) else None,
        "dividend":     round(float(row.get("Dividends", 0) or 0), 6),
        "split_factor": round(splits, 4) if splits != 0 else 1.0,
    }


def _fetch_history_one(stock: dict, period: str) -> bool:
    ticker = stock["ticker"]
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df is None or df.empty:
            if DEBUG_MODE:
                print(f"[history] {ticker}: empty response, skipping")
            return False
        records = [_map_history_row(stock["stock_uid"], ts, row) for ts, row in df.iterrows()]
        db.upsert_price_history_batch(records)
        return True
    except Exception as e:
        print(f"  XX {ticker}: {e}")
        return False


def _history_worker(
    work_queue: queue.Queue,
    period: str,
    rate_limit: float,
    stats: dict,
    lock: threading.Lock,
) -> None:
    while True:
        try:
            stock = work_queue.get(timeout=2)
        except queue.Empty:
            break

        success = _fetch_history_one(stock, period)
        time.sleep(rate_limit)

        with lock:
            if success:
                stats["ok"] += 1
            else:
                stats["failed"] += 1
            done = stats["ok"] + stats["failed"]
            status = "OK" if success else "XX"
            print(f"  {status} [{done}/{stats['total']}] {stock['ticker']}")

        work_queue.task_done()


def _run_history(
    rate_limit: float,
    num_workers: int,
    limit: int | None,
    period: str,
) -> None:
    pending = _get_pending_history(limit)
    if not pending:
        print("Price history is up to date.")
        return

    print(f"Fetching history ({period}) for {len(pending)} stocks  |  rate: {rate_limit}s/request  |  workers: {num_workers}")

    work_queue: queue.Queue = queue.Queue()
    for stock in pending:
        work_queue.put(stock)

    stats = {"ok": 0, "failed": 0, "total": len(pending)}
    lock = threading.Lock()

    threads = [
        threading.Thread(
            target=_history_worker,
            args=(work_queue, period, rate_limit, stats, lock),
            daemon=True,
        )
        for _ in range(num_workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nDone - {stats['ok']} fetched, {stats['failed']} failed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener enrichment worker")
    parser.add_argument("--rate",           type=float, default=0.5,  metavar="S",      help="Seconds between requests (default 0.5)")
    parser.add_argument("--workers",        type=int,   default=1,    metavar="N",      help="Parallel worker threads (default 1)")
    parser.add_argument("--limit",          type=int,   default=None, metavar="N",      help="Max stocks to process then exit")
    parser.add_argument("--ipo-only",       action="store_true",                        help="Run IPO calendar check only, then exit")
    parser.add_argument("--history-only",   action="store_true",                        help="Fetch price history only, then exit")
    parser.add_argument("--history-period", type=str,   default="5y", metavar="PERIOD", help="yfinance history period (default: 5y). Options: 1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max")
    args = parser.parse_args()

    run(
        rate_limit=args.rate,
        num_workers=args.workers,
        limit=args.limit,
        ipo_only=args.ipo_only,
        history_only=args.history_only,
        history_period=args.history_period,
    )


if __name__ == "__main__":
    main()
