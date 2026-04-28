"""
logistics.py — Midstream vessel monitoring: AIS chokepoints + Panama Canal draft restrictions.

AIS chokepoints use the aisstream.io free WebSocket API (requires free key registration).
Panama Canal restrictions are scraped from the public ACP restrictions page.

Both store results as source_signals and optionally create supply_chain_events candidates.

Key setup (one-time, AIS only):
    python -c "import sys,db; db.init_db(); db.set_api_key(1,'aisstream','YOUR_KEY')"
    Free key at https://aisstream.io

CLI:
    python src/logistics.py --chokepoints           # vessel counts at 10 chokepoints
    python src/logistics.py --chokepoints --dry-run # print counts without storing
    python src/logistics.py --panama                # Panama Canal draft restriction
    python src/logistics.py --all                   # both sources
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from datetime import datetime

import logging

import db
from utils_http import HttpClient
from screener_config import (
    DEBUG_MODE,
    LOGISTICS_USER_AGENT,
    EDGAR_RATE_LIMIT,
    AIS_API_BASE, AIS_API_KEY_NAME, AIS_SAMPLE_SECONDS,
    CHOKEPOINT_BASELINE_DAYS, CHOKEPOINT_LOW_THRESHOLD,
    SIGNAL_CHOKEPOINT, CHOKEPOINT_SCORE, PROVIDER_AIS,
    PANAMA_STATS_URL,
    SIGNAL_CANAL_DRAFT, CANAL_DRAFT_SCORE,
    CANAL_DRAFT_LOW_THRESHOLD, CANAL_NORMAL_DRAFT, PROVIDER_PANAMA,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
    EVENT_TYPE_INFRASTRUCTURE,
    CHOKEPOINTS,
)

_client = HttpClient({"User-Agent": LOGISTICS_USER_AGENT})

logger = logging.getLogger(__name__)

# Sectors impacted by chokepoint congestion — shipping + exposed industries
_CHOKEPOINT_SECTORS = ["Industrials", "Energy", "Materials", "Consumer Staples", "Technology"]


# ── AIS chokepoint monitoring ─────────────────────────────────────────────────

def fetch_chokepoint_vessel_counts(user_uid: int = 1, dry_run: bool = False) -> int:
    """Connect to aisstream.io, count vessels in each chokepoint bounding box for
    AIS_SAMPLE_SECONDS seconds, compare to stored baseline, and store signals where
    traffic is anomalously low (< CHOKEPOINT_LOW_THRESHOLD × baseline).

    Returns number of signals created.
    """
    api_key = db.get_api_key(user_uid, AIS_API_KEY_NAME)
    if not api_key:
        print("[AIS] No API key — set via db.set_api_key(1, 'aisstream', 'KEY')")
        print("[AIS] Free key at https://aisstream.io")
        return 0

    try:
        import websockets  # type: ignore
    except ImportError:
        print("[AIS] websockets not installed — run: pip install websockets")
        return 0

    counts = asyncio.run(_sample_ais(api_key, AIS_SAMPLE_SECONDS))
    if not counts:
        print("[AIS] No vessel data received.")
        return 0

    created = 0
    today   = datetime.now().strftime("%Y-%m-%d")

    for name, vessel_count in counts.items():
        cp        = CHOKEPOINTS[name]
        baseline  = _get_baseline_count(name)
        print(f"[AIS] {name}: {vessel_count} vessels  baseline={baseline:.1f}")

        if baseline <= 0:
            # First reading — store as baseline, no signal
            _store_baseline(name, vessel_count)
            continue

        ratio     = vessel_count / baseline
        signal_url = f"ais://{name.lower().replace(' ', '_')}/{today}"

        if dry_run:
            status = "LOW" if ratio < CHOKEPOINT_LOW_THRESHOLD else "normal"
            print(f"  → ratio={ratio:.2f}  [{status}]  (dry-run — not storing)")
            continue

        if db.signal_exists_by_url(PROVIDER_AIS, signal_url):
            logger.debug("[AIS] %s %s already stored — skip", name, today)
            _store_baseline(name, vessel_count)
            continue

        _store_baseline(name, vessel_count)

        if ratio >= CHOKEPOINT_LOW_THRESHOLD:
            continue  # traffic normal

        severity = SEVERITY_CRITICAL if ratio < 0.4 else SEVERITY_HIGH if ratio < CHOKEPOINT_LOW_THRESHOLD else SEVERITY_MEDIUM
        notes    = (
            f"Chokepoint '{name}': {vessel_count} vessels vs "
            f"{baseline:.0f} baseline ({ratio:.0%} of normal)"
        )
        print(f"[AIS] ALERT — {notes}")

        _store_logistics_signal(
            signal_type=SIGNAL_CHOKEPOINT,
            signal_url=signal_url,
            sub_score=CHOKEPOINT_SCORE,
            notes=notes,
            provider=PROVIDER_AIS,
            event_title=f"Chokepoint Congestion: {name}",
            region=name,
            lat=cp["lat"],
            lon=cp["lon"],
            severity=severity,
        )
        created += 1

    print(f"[AIS] Done — {created} chokepoint signals created.")
    return created


async def _sample_ais(api_key: str, duration_secs: int) -> dict[str, int]:
    """Open aisstream.io WebSocket, subscribe to all chokepoint bounding boxes,
    count vessel messages per chokepoint for duration_secs, then return counts.
    """
    try:
        import websockets  # type: ignore
    except ImportError:
        return {}

    counts: dict[str, int] = {name: 0 for name in CHOKEPOINTS}

    subscribe_msg = json.dumps({
        "APIKey": api_key,
        "BoundingBoxes": [
            [
                [cp["lat_min"], cp["lon_min"]],
                [cp["lat_max"], cp["lon_max"]],
            ]
            for cp in CHOKEPOINTS.values()
        ],
    })

    deadline = asyncio.get_event_loop().time() + duration_secs
    try:
        async with websockets.connect(AIS_API_BASE) as ws:
            await ws.send(subscribe_msg)
            while asyncio.get_event_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    msg = json.loads(raw)
                    pos = (msg.get("Message") or {}).get("PositionReport") or {}
                    lat = pos.get("Latitude")
                    lon = pos.get("Longitude")
                    if lat is None or lon is None:
                        continue
                    for name, cp in CHOKEPOINTS.items():
                        if cp["lat_min"] <= lat <= cp["lat_max"] and cp["lon_min"] <= lon <= cp["lon_max"]:
                            counts[name] += 1
                            break
                except asyncio.TimeoutError:
                    continue
    except Exception as exc:
        print(f"[AIS] WebSocket error: {exc}")

    return counts


def _get_baseline_count(chokepoint_name: str) -> float:
    """Return rolling average vessel count from stored source_signals for this chokepoint."""
    url_prefix = f"ais://{chokepoint_name.lower().replace(' ', '_')}/"
    rows = db.get_signals_by_source_url_prefix(PROVIDER_AIS, url_prefix, CHOKEPOINT_BASELINE_DAYS)
    if not rows:
        return 0.0
    counts: list[float] = []
    pattern = re.compile(r"(\d+) vessels")
    for row in rows:
        m = pattern.search(row.get("reason_text") or "")
        if m:
            counts.append(float(m.group(1)))
    return sum(counts) / len(counts) if counts else 0.0


def _store_baseline(chokepoint_name: str, vessel_count: int) -> None:
    """Persist a count observation against the first large shipping-sector stock
    so future _get_baseline_count() calls can compute a rolling average.
    stock_uid must be non-null; if no stock exists yet, silently skip.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    url   = f"ais://{chokepoint_name.lower().replace(' ', '_')}/{today}/baseline"
    if db.signal_exists_by_url(PROVIDER_AIS, url):
        return
    # Use the largest Industrials stock as the anchor row
    anchor = db.get_largest_stock_in_sector("Industrials")
    if not anchor:
        return
    db.upsert_source_signal({
        "stock_uid":   anchor["stock_uid"],
        "source":      PROVIDER_AIS,
        "signal_type": "chokepoint_baseline",
        "signal_url":  url,
        "sub_score":   0,
        "reason_text":       f"Chokepoint '{chokepoint_name}': {vessel_count} vessels",
    })


# ── Panama Canal draft restrictions ───────────────────────────────────────────

def fetch_panama_draft_restriction(user_uid: int = 1) -> int:
    """Scrape the Panama Canal Authority restrictions page and signal when
    the maximum allowed draft drops significantly below historical normal.

    Returns number of signals created.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    signal_url = f"panama://draft/{today}"

    if db.signal_exists_by_url(PROVIDER_PANAMA, signal_url):
        logger.debug("[Panama] %s already stored — skip", today)
        return 0

    try:
        r = _client.get(PANAMA_STATS_URL, timeout=30)
        r.raise_for_status()
        html = r.text
    except Exception as exc:
        print(f"[Panama] Failed to fetch restrictions page: {exc}")
        return 0

    # Parse current max draft from the restrictions HTML.
    # The ACP page shows values like "13.11 m / 43.0 ft" in a table.
    draft_m = _parse_panama_draft(html)
    if draft_m is None:
        print("[Panama] Could not parse draft restriction value from ACP page.")
        return 0

    drop = CANAL_NORMAL_DRAFT - draft_m
    print(f"[Panama] Current max draft: {draft_m:.2f} m  (normal: {CANAL_NORMAL_DRAFT} m, drop: {drop:+.2f} m)")

    if draft_m >= CANAL_DRAFT_LOW_THRESHOLD:
        print(f"[Panama] Draft {draft_m:.2f} m is within normal range — no signal.")
        return 0

    severity = SEVERITY_CRITICAL if draft_m < 11.0 else SEVERITY_HIGH if draft_m < 12.0 else SEVERITY_MEDIUM
    notes    = (
        f"Panama Canal max draft {draft_m:.2f} m "
        f"({drop:.2f} m below historical normal of {CANAL_NORMAL_DRAFT} m)"
    )
    print(f"[Panama] ALERT — {notes}")

    cp = CHOKEPOINTS["Panama Canal"]
    _store_logistics_signal(
        signal_type=SIGNAL_CANAL_DRAFT,
        signal_url=signal_url,
        sub_score=CANAL_DRAFT_SCORE,
        notes=notes,
        provider=PROVIDER_PANAMA,
        event_title=f"Panama Canal Draft Restriction — {draft_m:.2f} m",
        region="Panama Canal",
        lat=cp["lat"],
        lon=cp["lon"],
        severity=severity,
    )
    return 1


def _parse_panama_draft(html: str) -> float | None:
    """Extract max draft in metres from the ACP restrictions HTML."""
    # Look for patterns like "13.11 m", "12.80 m", etc.
    # The page typically shows the Neopanamax and Panamax restrictions.
    patterns = [
        r"(\d{1,2}\.\d{1,2})\s*m\b",   # decimal metres
        r"(\d{1,2}\.\d{1,2})\s*metros", # Spanish "metros"
    ]
    values: list[float] = []
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            v = float(m.group(1))
            if 8.0 <= v <= 16.0:   # sanity range for canal draft
                values.append(v)
    if not values:
        return None
    # Return the minimum restriction (most limiting constraint)
    return min(values)


# ── Shared helper ─────────────────────────────────────────────────────────────

def _store_logistics_signal(
    signal_type: str,
    signal_url: str,
    sub_score: float,
    notes: str,
    provider: str,
    event_title: str,
    region: str,
    lat: float,
    lon: float,
    severity: str,
) -> None:
    """Store source_signal rows for all shipping-exposed stocks and optionally
    create a supply_chain_events candidate.
    """
    stocks = db.get_large_cap_stocks_by_sectors(_CHOKEPOINT_SECTORS, limit=30)
    for stock in stocks:
        db.upsert_source_signal({
            "stock_uid":   stock["stock_uid"],
            "source":      provider,
            "signal_type": signal_type,
            "signal_url":  signal_url,
            "sub_score":   sub_score,
            "reason_text":       notes,
        })

    # Create supply_chain_events candidate for HIGH/CRITICAL severity
    if severity in (SEVERITY_HIGH, SEVERITY_CRITICAL):
        import json as _json
        db.upsert_supply_chain_event({
            "title":               event_title,
            "event_type":          EVENT_TYPE_INFRASTRUCTURE,
            "region":              region,
            "lat":                 lat,
            "lon":                 lon,
            "severity":            severity,
            "status":              "monitoring",
            "event_date":          datetime.now().strftime("%Y-%m-%d"),
            "affected_sectors":    _json.dumps(_CHOKEPOINT_SECTORS),
            "beneficiary_sectors": _json.dumps(["Industrials"]),
        })


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener logistics / midstream signals")
    parser.add_argument("--chokepoints", action="store_true", help="AIS vessel counts at 10 chokepoints")
    parser.add_argument("--panama",      action="store_true", help="Panama Canal draft restriction")
    parser.add_argument("--all",         action="store_true", help="Run all logistics sources")
    parser.add_argument("--dry-run",     action="store_true", help="Print results without storing signals")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    db.init_db()

    if args.all or args.chokepoints:
        fetch_chokepoint_vessel_counts(dry_run=args.dry_run)

    if args.all or args.panama:
        fetch_panama_draft_restriction()


if __name__ == "__main__":
    main()
