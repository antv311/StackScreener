"""
seeder.py — One-time database initialization.

Usage:
    python seeder.py                # init schema + seed admin + fetch full NYSE/NASDAQ universe
    python seeder.py --schema-only  # init schema and admin only, skip ticker fetch
    python seeder.py --limit 100    # fetch at most 100 tickers (useful for testing)
"""

import argparse
import time

import yfinance as yf

import db

_PAGE_SIZE = 250

_EXCHANGES: dict[str, str] = {
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NYQ": "NYSE",
    "NYE": "NYSE",
}


def _screener_row_to_stock(row: dict, exchange_label: str) -> dict | None:
    ticker = row.get("symbol")
    if not ticker:
        return None
    return {
        "ticker":        ticker.upper().replace(".", "-"),
        "exchange":      exchange_label,
        "market_index":  exchange_label,
        "sector":        row.get("sector"),
        "industry":      row.get("industry"),
        "market_cap":    row.get("marketCap"),
        "price":         row.get("regularMarketPrice") or 0.0,
        "change_pct":    row.get("regularMarketChangePercent"),
        "current_volume": row.get("regularMarketVolume"),
        "average_volume": row.get("averageVolume3Month") or row.get("averageDailyVolume3Month"),
    }


def _fetch_page(exchange_code: str, offset: int) -> dict:
    q = yf.EquityQuery("eq", ["exchange", exchange_code])
    return yf.screen(q, sortField="ticker", sortAsc=True, size=_PAGE_SIZE, offset=offset)


def fetch_universe(limit: int | None = None) -> int:
    total_inserted = 0

    for code, label in _EXCHANGES.items():
        offset = 0
        exchange_total: int | None = None
        print(f"\n  {code} ({label})")

        while True:
            try:
                response = _fetch_page(code, offset)
            except Exception as e:
                print(f"    error at offset {offset}: {e}")
                break

            quotes = response.get("quotes", [])

            if exchange_total is None:
                raw_total = response.get("total", 0)
                exchange_total = raw_total.get("value", 0) if isinstance(raw_total, dict) else int(raw_total)
                print(f"    total listed: {exchange_total}")

            if not quotes:
                break

            records = [r for row in quotes if (r := _screener_row_to_stock(row, label))]
            if records:
                db.upsert_stocks_batch(records)
                total_inserted += len(records)

            offset += len(quotes)
            print(f"    {offset}/{exchange_total} fetched ({total_inserted} total inserted)")

            if limit and total_inserted >= limit:
                print(f"    --limit {limit} reached")
                return total_inserted

            if offset >= (exchange_total or 0):
                break

            time.sleep(0.3)

    return total_inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener database seeder")
    parser.add_argument("--schema-only", action="store_true", help="Init schema only, skip ticker fetch")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="Fetch at most N tickers")
    args = parser.parse_args()

    print("Initializing schema...")
    db.init_db()
    print("  OK")

    print("Seeding default user...")
    db.seed_default_user()
    print("  OK — login: admin / admin (you will be prompted to change this on first launch)")

    if args.schema_only:
        print("\nDone.")
        return

    print("\nFetching ticker universe from Yahoo Finance...")
    count = fetch_universe(limit=args.limit)
    print(f"\nDone. {count} stocks seeded. Run enricher.py to fill in fundamentals.")


if __name__ == "__main__":
    main()
