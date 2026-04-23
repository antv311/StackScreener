"""
commodities.py — Upstream commodity signals: USDA crop conditions + EIA petroleum inventory.

Both APIs are free with a registration key. Keys stored in api_keys table.
Results land in source_signals (type crop_stress / oil_inventory_surprise) and
optionally create supply_chain_events candidates (status=monitoring) when severe.

Key setup (one-time):
    python -c "import sys,db; db.init_db(); db.set_api_key(1,'usda_nass','YOUR_KEY')"
    python -c "import sys,db; db.init_db(); db.set_api_key(1,'eia','YOUR_KEY')"

CLI:
    python src/commodities.py --usda-crops                # USDA weekly crop conditions
    python src/commodities.py --usda-crops --year 2024    # specific year
    python src/commodities.py --eia-petroleum             # EIA weekly crude oil inventory
    python src/commodities.py --all                       # both sources
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta

import requests

sys.path.insert(0, __file__.replace("commodities.py", ""))
import db
from screener_config import (
    DEBUG_MODE,
    EDGAR_RATE_LIMIT,
    USDA_API_BASE, USDA_API_KEY_NAME,
    SIGNAL_CROP_STRESS, CROP_STRESS_SCORE,
    CROP_GOOD_EXCELLENT_THRESHOLD, PROVIDER_USDA,
    EIA_API_BASE, EIA_API_KEY_NAME,
    SIGNAL_OIL_INVENTORY, OIL_SURPRISE_SCORE,
    OIL_SURPRISE_THRESHOLD, PROVIDER_EIA,
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
    EVENT_TYPE_NATURAL_DISASTER,
)

_HEADERS = {"User-Agent": "StackScreener/1.0 commodities@stackscreener.local"}

# Crop → affected stock sectors (used when promoting to supply_chain_events)
_CROP_SECTORS: dict[str, list[str]] = {
    "CORN":       ["Consumer Staples", "Energy", "Materials"],
    "SOYBEANS":   ["Consumer Staples", "Materials"],
    "WHEAT":      ["Consumer Staples"],
    "COTTON":     ["Consumer Discretionary", "Materials"],
    "RICE":       ["Consumer Staples"],
}

# EIA series IDs for weekly petroleum inventories
_EIA_CRUDE_SERIES   = "PET.WCRSTUS1.W"   # US total crude oil stocks (thousand barrels)
_EIA_GASOLINE_SERIES = "PET.WGTSTUS1.W"  # US total gasoline stocks


# ── USDA NASS Crop Conditions ─────────────────────────────────────────────────

def fetch_usda_crops(year: int | None = None, user_uid: int = 1) -> int:
    """Fetch USDA NASS weekly crop condition data and store crop-stress signals.

    Returns number of signals created.
    """
    api_key = db.get_api_key(user_uid, USDA_API_KEY_NAME)
    if not api_key:
        print(f"[USDA] No API key — set via db.set_api_key(1, 'usda_nass', 'KEY')")
        print(f"[USDA] Free key at https://quickstats.nass.usda.gov/api")
        return 0

    if year is None:
        year = datetime.now().year

    created = 0
    for crop, sectors in _CROP_SECTORS.items():
        try:
            params = {
                "key":          api_key,
                "source_desc":  "SURVEY",
                "sector_desc":  "CROPS",
                "commodity_desc": crop,
                "statisticcat_desc": "CONDITION",
                "unit_desc":    "PCT EXCELLENT",
                "year":         year,
                "agg_level_desc": "NATIONAL",
                "format":       "JSON",
            }
            r = requests.get(USDA_API_BASE, params=params, headers=_HEADERS, timeout=30)
            r.raise_for_status()
            data  = r.json().get("data") or []
            if not data:
                if DEBUG_MODE:
                    print(f"[USDA] No CONDITION data for {crop} {year}")
                continue

            # latest week
            rows = sorted(data, key=lambda x: x.get("week_ending") or "", reverse=True)
            latest = rows[0]
            pct_excellent = float(latest.get("Value") or 0) / 100.0

            # also fetch PCT GOOD
            params2 = dict(params)
            params2["unit_desc"] = "PCT GOOD"
            r2 = requests.get(USDA_API_BASE, params=params2, headers=_HEADERS, timeout=30)
            r2.raise_for_status()
            data2 = r2.json().get("data") or []
            rows2 = sorted(data2, key=lambda x: x.get("week_ending") or "", reverse=True)
            pct_good = float(rows2[0].get("Value") or 0) / 100.0 if rows2 else 0.0

            good_excellent = pct_excellent + pct_good
            week_ending    = latest.get("week_ending") or ""
            signal_url     = f"usda://{crop}/{year}/{week_ending}"

            if db.signal_exists_by_url(PROVIDER_USDA, signal_url):
                if DEBUG_MODE:
                    print(f"[USDA] {crop} week {week_ending} already stored — skip")
                continue

            # Determine severity vs. historical threshold
            # Good+Excellent < 50% is historically poor; < 40% is crisis
            if good_excellent < 0.40:
                severity  = SEVERITY_HIGH
                sub_score = CROP_STRESS_SCORE + 10
            elif good_excellent < 0.50:
                severity  = SEVERITY_MEDIUM
                sub_score = CROP_STRESS_SCORE
            else:
                severity  = SEVERITY_LOW
                sub_score = CROP_STRESS_SCORE - 10

            notes = (
                f"{crop} condition week {week_ending}: "
                f"Good={pct_good:.0%} Excellent={pct_excellent:.0%} "
                f"Combined={good_excellent:.0%}"
            )
            print(f"[USDA] {notes}")

            # Store against a generic commodity stock (use cash proxy ETF tickers if present)
            _store_commodity_signal(
                signal_type=SIGNAL_CROP_STRESS,
                signal_url=signal_url,
                sub_score=sub_score,
                notes=notes,
                provider=PROVIDER_USDA,
                sectors=sectors,
            )
            created += 1
            time.sleep(EDGAR_RATE_LIMIT)

        except Exception as exc:
            print(f"[USDA] {crop} error: {exc}")

    print(f"[USDA] Done — {created} crop-stress signals created.")
    return created


# ── EIA Weekly Petroleum Inventory ────────────────────────────────────────────

def fetch_eia_petroleum(user_uid: int = 1) -> int:
    """Fetch EIA weekly crude oil inventory and flag surprise moves as signals.

    Returns number of signals created.
    """
    api_key = db.get_api_key(user_uid, EIA_API_KEY_NAME)
    if not api_key:
        print(f"[EIA] No API key — set via db.set_api_key(1, 'eia', 'KEY')")
        print(f"[EIA] Free key at https://www.eia.gov/opendata/")
        return 0

    created = 0
    for series_id, label in [(_EIA_CRUDE_SERIES, "Crude Oil"), (_EIA_GASOLINE_SERIES, "Gasoline")]:
        try:
            url    = f"{EIA_API_BASE}/seriesid/{series_id}"
            params = {"api_key": api_key, "out": "json"}
            r      = requests.get(url, params=params, headers=_HEADERS, timeout=30)
            r.raise_for_status()
            payload = r.json()
            series  = (payload.get("response") or {}).get("data") or []
            if not series:
                # v1 API format fallback
                series = (payload.get("series") or [{}])[0].get("data") or []
                # v1 data is [[period, value], ...]
                series = [{"period": row[0], "value": row[1]} for row in series]

            # Sort desc, take 6 weeks
            series = sorted(series, key=lambda x: x.get("period") or "", reverse=True)[:6]
            if len(series) < 2:
                if DEBUG_MODE:
                    print(f"[EIA] Insufficient data for {label}")
                continue

            latest_val  = float(series[0].get("value") or 0)
            latest_period = str(series[0].get("period") or "")
            baseline    = sum(float(s.get("value") or 0) for s in series[1:]) / max(1, len(series) - 1)
            pct_change  = (latest_val - baseline) / max(1, abs(baseline))

            signal_url = f"eia://{series_id}/{latest_period}"
            if db.signal_exists_by_url(PROVIDER_EIA, signal_url):
                if DEBUG_MODE:
                    print(f"[EIA] {label} {latest_period} already stored — skip")
                continue

            if abs(pct_change) < OIL_SURPRISE_THRESHOLD:
                if DEBUG_MODE:
                    print(f"[EIA] {label} {latest_period}: change {pct_change:.1%} within threshold — skip")
                continue

            direction = "BUILD" if pct_change > 0 else "DRAW"
            severity  = SEVERITY_HIGH if abs(pct_change) > 0.10 else SEVERITY_MEDIUM
            sub_score = OIL_SURPRISE_SCORE if direction == "DRAW" else OIL_SURPRISE_SCORE - 20
            notes = (
                f"{label} inventory {direction} week {latest_period}: "
                f"{latest_val:,.0f} kb vs {baseline:,.0f} kb baseline "
                f"({pct_change:+.1%})"
            )
            print(f"[EIA] {notes}")

            _store_commodity_signal(
                signal_type=SIGNAL_OIL_INVENTORY,
                signal_url=signal_url,
                sub_score=sub_score,
                notes=notes,
                provider=PROVIDER_EIA,
                sectors=["Energy"],
            )
            created += 1
            time.sleep(EDGAR_RATE_LIMIT)

        except Exception as exc:
            print(f"[EIA] {label} error: {exc}")

    print(f"[EIA] Done — {created} oil-inventory signals created.")
    return created


# ── Shared helper ─────────────────────────────────────────────────────────────

def _store_commodity_signal(
    signal_type: str,
    signal_url: str,
    sub_score: float,
    notes: str,
    provider: str,
    sectors: list[str],
) -> None:
    """Store a commodity signal against all enriched stocks in the affected sectors."""
    # Find stocks in affected sectors — limit to large-cap to keep noise low
    placeholders = ", ".join("?" * len(sectors))
    stocks = db.query(
        f"SELECT stock_uid, ticker, sector FROM stocks "
        f"WHERE delisted = 0 AND sector IN ({placeholders}) "
        f"AND market_cap >= 1e9 "
        f"ORDER BY market_cap DESC LIMIT 20",
        sectors,
    )

    for stock in stocks:
        db.upsert_source_signal({
            "stock_uid":   stock["stock_uid"],
            "source":      provider,
            "signal_type": signal_type,
            "signal_url":  signal_url,
            "sub_score":   sub_score,
            "reason_text":       notes,
        })


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener commodity signals")
    parser.add_argument("--usda-crops",   action="store_true", help="USDA NASS weekly crop conditions")
    parser.add_argument("--eia-petroleum",action="store_true", help="EIA weekly petroleum inventory")
    parser.add_argument("--all",          action="store_true", help="Run all commodity sources")
    parser.add_argument("--year",         type=int,            help="--usda-crops: survey year (default: current)")
    args = parser.parse_args()

    db.init_db()

    if args.all or args.usda_crops:
        fetch_usda_crops(year=args.year)

    if args.all or args.eia_petroleum:
        fetch_eia_petroleum()


if __name__ == "__main__":
    main()
