"""
screener_run.py — Scan runner and CLI entry point for StackScreener.

Orchestrates a full scoring pass over the active stock universe,
saves results to the database, and exports to CSV.

Scan modes:
  nsr        Normal Stock Ranking — all active stocks scored by fundamentals
  thematic   Supply-chain-aware — universe filtered to disruption-relevant sectors
  watchlist  Only stocks on a named watchlist

Usage:
    python screener_run.py
    python screener_run.py --mode thematic
    python screener_run.py --mode watchlist --watchlist "My List"
    python screener_run.py --limit 500
    python screener_run.py --top 25
    python screener_run.py --no-csv
"""

import argparse
import csv
import json
import os
from datetime import datetime

import db
import screener
from screener_config import (
    SCAN_TOP_N,
    SCAN_MODE_NSR, SCAN_MODE_THEMATIC, SCAN_MODE_WATCHLIST,
    SEVERITY_RANK, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM,
    DEBUG_MODE,
)

_RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "Results")

_CONFIDENCE_MULT: dict[str, float] = {
    CONFIDENCE_HIGH:   1.0,
    CONFIDENCE_MEDIUM: 0.75,
    "low":             0.50,
}


# ── Signal pre-computation ─────────────────────────────────────────────────────

def _build_supply_chain_scores() -> dict[int, float]:
    """Map stock_uid → supply chain beneficiary score (0–100)."""
    scores: dict[int, float] = {}
    for link in db.get_active_event_stocks():
        if link["role"] != "beneficiary":
            continue
        sev_score = SEVERITY_RANK.get(link["severity"], 1) * 25.0  # max 100 for CRITICAL
        conf_mult = _CONFIDENCE_MULT.get(link["confidence"] or "medium", 0.75)
        val = min(100.0, sev_score * conf_mult)
        stock_uid = link["stock_uid"]
        scores[stock_uid] = max(scores.get(stock_uid, 0.0), val)
    return scores


def _build_inst_flow_scores() -> dict[int, float]:
    """Map stock_uid → institutional flow score (0–100) from source_signals."""
    rows = db.get_all_signal_scores()
    bucket: dict[int, list[float]] = {}
    for row in rows:
        bucket.setdefault(row["stock_uid"], []).append(float(row["sub_score"]))
    return {uid: min(100.0, sum(vals) / len(vals)) for uid, vals in bucket.items()}


# ── Universe loading ───────────────────────────────────────────────────────────

def _thematic_universe() -> list[dict]:
    """Return stocks in sectors/industries relevant to active supply chain events."""
    events = db.get_active_event_sectors()
    if not events:
        if DEBUG_MODE:
            print("[screener_run] no active events — falling back to full NSR universe")
        return db.get_active_stocks()

    # Collect all beneficiary + affected sectors/industries
    sector_set: set[str] = set()
    for ev in events:
        for field in ("beneficiary_sectors", "affected_sectors", "affected_industries"):
            for item in json.loads(ev.get(field) or "[]"):
                sector_set.add(item)

    # Stocks explicitly linked as beneficiaries
    linked_uids: set[int] = {
        link["stock_uid"]
        for link in db.get_active_event_stocks()
        if link["role"] == "beneficiary"
    }

    all_stocks = db.get_active_stocks()
    return [
        s for s in all_stocks
        if s["stock_uid"] in linked_uids
        or s.get("sector") in sector_set
        or s.get("industry") in sector_set
    ]


def _load_universe(mode: str, watchlist_name: str | None, limit: int | None) -> list[dict]:
    match mode:
        case "watchlist":
            if not watchlist_name:
                raise ValueError("--watchlist NAME is required for watchlist mode")
            wl = db.get_watchlist_by_name(watchlist_name)
            if not wl:
                raise ValueError(f"Watchlist '{watchlist_name}' not found")
            stocks = db.get_watchlist_stocks(wl["watchlist_uid"])
        case "thematic":
            stocks = _thematic_universe()
        case _:
            stocks = db.get_active_stocks()

    if limit is not None:
        stocks = stocks[:limit]
    return stocks


# ── CSV export ─────────────────────────────────────────────────────────────────

_CSV_FIELDS = [
    "composite_rank", "ticker", "exchange", "sector",
    "composite_score",
    "score_ev_revenue", "score_pe", "score_ev_ebitda",
    "score_profit_margin", "score_peg", "score_debt_equity",
    "score_cfo_ratio", "score_altman_z",
    "score_supply_chain", "score_inst_flow",
    "price", "market_cap",
]


def _export_csv(results: list[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "results.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    return path


# ── Core scan ─────────────────────────────────────────────────────────────────

def run_scan(
    mode: str = SCAN_MODE_NSR,
    triggered_by: str = "manual",
    watchlist_name: str | None = None,
    limit: int | None = None,
    top_n: int = SCAN_TOP_N,
    export_csv: bool = True,
) -> int:
    """Run a full scan. Returns scan_uid."""
    scan_uid = db.create_scan(mode, triggered_by)
    print(f"\nScan #{scan_uid} | mode={mode} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        stocks = _load_universe(mode, watchlist_name, limit)
    except ValueError as e:
        db.fail_scan(scan_uid, str(e))
        print(f"  Failed: {e}")
        return scan_uid

    symbol_count = len(stocks)
    print(f"Universe: {symbol_count} stocks")

    sc_scores = _build_supply_chain_scores()
    if_scores = _build_inst_flow_scores()

    scored: list[dict] = []
    failed = 0

    for stock in stocks:
        uid = stock["stock_uid"]
        try:
            components = screener.score_stock(
                stock,
                supply_chain_score=sc_scores.get(uid, 0.0),
                inst_flow_score=if_scores.get(uid, 0.0),
            )
            row = {
                "stock_uid":         uid,
                "scan_uid":          scan_uid,
                "price_at_scan":     stock.get("price"),
                "market_cap_at_scan": stock.get("market_cap"),
                # stock fields carried through for CSV / display
                "ticker":            stock["ticker"],
                "exchange":          stock["exchange"],
                "sector":            stock.get("sector"),
                "price":             stock.get("price"),
                "market_cap":        stock.get("market_cap"),
                **components,
            }
            scored.append(row)
        except Exception as e:
            failed += 1
            if DEBUG_MODE:
                print(f"[screener_run] {stock['ticker']} score failed: {e}")

    # Rank by composite_score descending
    scored.sort(key=lambda r: r["composite_score"], reverse=True)
    for rank, row in enumerate(scored, 1):
        row["composite_rank"] = rank

    # Persist to scan_results
    for row in scored:
        db.insert_scan_result({
            "stock_uid":          row["stock_uid"],
            "scan_uid":           row["scan_uid"],
            "composite_score":    row["composite_score"],
            "composite_rank":     row["composite_rank"],
            "score_ev_revenue":   row["score_ev_revenue"],
            "score_pe":           row["score_pe"],
            "score_ev_ebitda":    row["score_ev_ebitda"],
            "score_profit_margin": row["score_profit_margin"],
            "score_peg":          row["score_peg"],
            "score_debt_equity":  row["score_debt_equity"],
            "score_cfo_ratio":    row["score_cfo_ratio"],
            "score_altman_z":     row["score_altman_z"],
            "score_supply_chain": row["score_supply_chain"],
            "score_inst_flow":    row["score_inst_flow"],
            "price_at_scan":      row["price_at_scan"],
            "market_cap_at_scan": row["market_cap_at_scan"],
        })

    db.complete_scan(scan_uid, symbol_count, len(scored), failed)

    # Print top N
    top = scored[:top_n]
    print(f"\nTop {len(top)} results (of {len(scored)} scored):\n")
    print(f"{'Rank':<5} {'Ticker':<8} {'Exchange':<9} {'Sector':<32} {'Score':>6}  {'Price':>8}  {'SC':>5}  {'Flow':>5}")
    print("-" * 86)
    for row in top:
        print(
            f"  {row['composite_rank']:<4} {row['ticker']:<8} {row['exchange']:<9} "
            f"{(row.get('sector') or ''):<32} {row['composite_score']:>6.1f}  "
            f"{(row.get('price') or 0.0):>8.2f}  "
            f"{row['score_supply_chain']:>5.0f}  {row['score_inst_flow']:>5.0f}"
        )

    if export_csv:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(_RESULTS_DIR, mode, ts)
        path = _export_csv(top, out_dir)
        print(f"\nCSV: {path}")

    print(f"\nDone — {len(scored)} scored, {failed} failed.")
    return scan_uid


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener scan runner")
    parser.add_argument(
        "--mode", choices=["nsr", "thematic", "watchlist"], default="nsr",
        help="Scan mode (default: nsr)",
    )
    parser.add_argument("--watchlist", metavar="NAME", help="Watchlist name for watchlist mode")
    parser.add_argument("--limit",  type=int, default=None, metavar="N", help="Score at most N stocks")
    parser.add_argument("--top",    type=int, default=SCAN_TOP_N, metavar="N", help=f"Show top N results (default {SCAN_TOP_N})")
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV export")
    args = parser.parse_args()

    db.init_db()
    run_scan(
        mode=args.mode,
        watchlist_name=args.watchlist,
        limit=args.limit,
        top_n=args.top,
        export_csv=not args.no_csv,
    )


if __name__ == "__main__":
    main()
