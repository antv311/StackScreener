"""
enricher.py — Background worker that fills in full fundamentals for seeded stocks.

Reads stocks with NULL or stale fundamentals and enriches them via yfinance,
one at a time with configurable rate limiting. Safe to kill and restart —
progress is committed after each stock.

Usage:
    python enricher.py              # run until all stocks are up to date
    python enricher.py --rate 0.5   # seconds between requests (default 0.5)
    python enricher.py --limit 100  # process at most 100 stocks then exit
"""

import argparse
import queue
import threading
import time
from datetime import datetime

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
        print(f"  ✗ {ticker}: {e}")
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
            status = "✓" if success else "✗"
            print(f"  {status} [{done}/{stats['total']}] {stock['ticker']}")

        work_queue.task_done()


def run(rate_limit: float = 0.5, num_workers: int = 1, limit: int | None = None) -> None:
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
        threading.Thread(
            target=_worker,
            args=(work_queue, rate_limit, stats, lock),
            daemon=True,
        )
        for _ in range(num_workers)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nDone — {stats['ok']} enriched, {stats['failed']} failed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener enrichment worker")
    parser.add_argument("--rate",    type=float, default=0.5,  metavar="S", help="Seconds between requests (default 0.5)")
    parser.add_argument("--workers", type=int,   default=1,    metavar="N", help="Parallel worker threads (default 1)")
    parser.add_argument("--limit",   type=int,   default=None, metavar="N", help="Max stocks to process then exit")
    args = parser.parse_args()

    run(rate_limit=args.rate, num_workers=args.workers, limit=args.limit)


if __name__ == "__main__":
    main()
