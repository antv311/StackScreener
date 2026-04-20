"""
edgar.py — SEC EDGAR data pipeline for StackScreener.

Three pipelines, all free (no API key required):

  XBRL structured facts (geographic revenue, customer concentration):
    1. --seed-ciks      Map every ticker to its SEC CIK (run once, idempotent).
    2. --fetch-facts    Pull XBRL geographic revenue + customer concentration.

  10-K text extraction (supply chain risk flags, customer % mentions):
    3. --fetch-filings  Download latest 10-K via edgartools; extract risk flags
                        and customer percentage mentions; store as edgar_facts.

Usage:
    python edgar.py --seed-ciks
    python edgar.py --fetch-facts [--limit N]
    python edgar.py --fetch-filings [--limit N]
    python edgar.py --china-exposure 0.15
"""

import argparse
import json
import re
import time
from datetime import datetime, timedelta

import requests

import db
from screener_config import (
    DEBUG_MODE,
    EDGAR_RATE_LIMIT, EDGAR_STALENESS_DAYS, EDGAR_FILING_STALENESS, EDGAR_IDENTITY,
    FACT_GEOGRAPHIC_REVENUE, FACT_CUSTOMER_CONCENTRATION,
    FACT_RISK_FLAGS, FACT_FILING_CUSTOMERS,
)

_EDGAR_HEADERS = {"User-Agent": "StackScreener antv311@gmail.com"}

_CIK_MAP_URL    = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL      = "https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"

# XBRL concept names used for geographic revenue extraction.
# Companies use different concepts; we try each in order.
_GEO_REVENUE_CONCEPTS = [
    "RevenueFromExternalCustomersByGeographicAreas",
    "SegmentReportingInformationRevenue",
    "Revenues",
]

# Geographic label normalisation — map raw XBRL segment labels to clean keys.
_GEO_LABEL_MAP: dict[str, str] = {
    "united states":            "US",
    "united states of america": "US",
    "us":                       "US",
    "domestic":                 "US",
    "china":                    "China",
    "greater china":            "China",
    "peoples republic of china":"China",
    "europe":                   "Europe",
    "rest of europe":           "Europe",
    "asia":                     "Asia",
    "asia pacific":             "Asia Pacific",
    "japan":                    "Japan",
    "rest of world":            "Other",
    "other":                    "Other",
    "international":            "International",
}


def _norm_geo_label(raw: str) -> str:
    return _GEO_LABEL_MAP.get(raw.strip().lower(), raw.strip().title())


# ── CIK seeding ────────────────────────────────────────────────────────────────

def seed_ciks() -> None:
    """Download the SEC ticker→CIK map and update every matching stock."""
    print("Fetching SEC ticker→CIK map...")
    resp = requests.get(_CIK_MAP_URL, headers=_EDGAR_HEADERS, timeout=30)
    resp.raise_for_status()
    cik_data = resp.json()

    # Build ticker→cik_str lookup (CIK zero-padded to 10 digits for API calls)
    ticker_to_cik: dict[str, str] = {
        entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
        for entry in cik_data.values()
    }

    stocks = db.query("SELECT stock_uid, ticker FROM stocks WHERE cik IS NULL")
    updated = 0
    for stock in stocks:
        cik = ticker_to_cik.get(stock["ticker"].upper())
        if cik:
            db.execute(
                "UPDATE stocks SET cik = ? WHERE stock_uid = ?",
                (cik, stock["stock_uid"]),
            )
            updated += 1

    total = len(stocks)
    print(f"CIK seed complete: {updated}/{total} stocks matched ({total - updated} unmatched).")


# ── XBRL fact extraction ───────────────────────────────────────────────────────

def _fetch_company_facts(cik: str) -> dict | None:
    url = _FACTS_URL.format(cik=cik)
    try:
        resp = requests.get(url, headers=_EDGAR_HEADERS, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        if DEBUG_MODE:
            print(f"[edgar] facts fetch failed for CIK {cik}: {e}")
        return None


def _extract_geographic_revenue(facts: dict) -> dict[str, dict[str, float]]:
    """Extract geographic revenue breakdown by fiscal year.

    Returns {period: {region: fraction_of_total}, ...}
    where fractions sum to ~1.0 (best-effort normalisation).
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    results: dict[str, dict[str, float]] = {}

    for concept in _GEO_REVENUE_CONCEPTS:
        if concept not in us_gaap:
            continue
        units = us_gaap[concept].get("units", {})
        usd_facts = units.get("USD", [])

        # Group by fiscal year and segment label
        by_year: dict[str, dict[str, float]] = {}
        for fact in usd_facts:
            if fact.get("form") not in ("10-K", "10-K/A"):
                continue
            if fact.get("frame") or not fact.get("end"):
                pass
            period = fact["end"][:4]  # fiscal year from end date
            label = _norm_geo_label(fact.get("segment", {}).get("value", "") or "Total")
            val = float(fact.get("val", 0))
            if val <= 0:
                continue
            by_year.setdefault(period, {})[label] = val

        # Normalise each year's values to fractions
        for period, segments in by_year.items():
            total = sum(segments.values())
            if total > 0 and len(segments) > 1:
                results[period] = {k: round(v / total, 4) for k, v in segments.items()}

        if results:
            break  # found data from this concept — don't try the next one

    return results


def _extract_customer_concentration(facts: dict) -> dict[str, list[dict]]:
    """Extract major customer concentration percentages by fiscal year.

    Returns {period: [{name, pct, segment}, ...], ...}
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    concept = "ConcentrationRiskPercentage1"
    if concept not in us_gaap:
        return {}

    results: dict[str, list[dict]] = {}
    for fact in us_gaap[concept].get("units", {}).get("pure", []):
        if fact.get("form") not in ("10-K", "10-K/A"):
            continue
        segment = fact.get("segment", {})
        if not segment:
            continue
        period = fact["end"][:4]
        pct = round(float(fact.get("val", 0)), 4)
        if pct <= 0:
            continue
        entry = {
            "name":    segment.get("value", "Unknown"),
            "pct":     pct,
            "segment": fact.get("accn", ""),
        }
        results.setdefault(period, []).append(entry)

    return results


def _store_facts(stock_uid: int, geo: dict, customers: dict) -> int:
    """Write extracted facts to edgar_facts. Returns number of rows upserted."""
    count = 0
    for period, value in geo.items():
        db.upsert_edgar_fact({
            "stock_uid":  stock_uid,
            "fact_type":  FACT_GEOGRAPHIC_REVENUE,
            "period":     period,
            "value_json": json.dumps(value),
        })
        count += 1
    for period, value in customers.items():
        db.upsert_edgar_fact({
            "stock_uid":  stock_uid,
            "fact_type":  FACT_CUSTOMER_CONCENTRATION,
            "period":     period,
            "value_json": json.dumps(value),
        })
        count += 1
    return count


# ── Pending query ──────────────────────────────────────────────────────────────

def _get_pending_facts(limit: int | None = None) -> list[dict]:
    """Return stocks with a CIK whose EDGAR facts are missing or stale."""
    cutoff = (datetime.now() - timedelta(days=EDGAR_STALENESS_DAYS)).strftime("%Y-%m-%d")
    sql = """
        SELECT s.stock_uid, s.ticker, s.cik
        FROM stocks s
        WHERE s.cik IS NOT NULL
          AND s.delisted = 0
          AND NOT EXISTS (
              SELECT 1 FROM edgar_facts ef
              WHERE ef.stock_uid = s.stock_uid
                AND ef.fetched_at >= ?
          )
        ORDER BY s.ticker ASC
    """
    params: tuple = (cutoff,)
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return db.query(sql, params)


# ── Main fetch loop ────────────────────────────────────────────────────────────

def fetch_facts(limit: int | None = None) -> None:
    pending = _get_pending_facts(limit)
    if not pending:
        print("EDGAR facts are up to date.")
        return

    print(f"Fetching EDGAR XBRL facts for {len(pending)} stocks...")
    ok = failed = skipped = 0

    for i, stock in enumerate(pending, 1):
        facts = _fetch_company_facts(stock["cik"])
        time.sleep(EDGAR_RATE_LIMIT)

        if not facts:
            failed += 1
            print(f"  XX [{i}/{len(pending)}] {stock['ticker']}: no data")
            continue

        geo       = _extract_geographic_revenue(facts)
        customers = _extract_customer_concentration(facts)

        if not geo and not customers:
            skipped += 1
            if DEBUG_MODE:
                print(f"[edgar] {stock['ticker']}: no geographic or customer facts in XBRL")
            continue

        rows = _store_facts(stock["stock_uid"], geo, customers)
        ok += 1
        print(f"  OK [{i}/{len(pending)}] {stock['ticker']}: {rows} fact rows")

    print(f"\nDone - {ok} fetched, {skipped} no XBRL data, {failed} failed.")


# ── 10-K text pipeline (edgartools) ───────────────────────────────────────────

# Supply chain risk keyword groups — each key becomes a boolean flag in FACT_RISK_FLAGS.
_RISK_FLAG_PATTERNS: dict[str, list[str]] = {
    "china_dependency":     ["china", "chinese", "prc", "people's republic"],
    "taiwan_risk":          ["taiwan", "tsmc", "taiwan strait"],
    "single_supplier_risk": ["sole source", "single source", "sole supplier",
                             "single supplier", "rely on a single supplier"],
    "tariff_risk":          ["tariff", "trade war", "import duty",
                             "trade restriction", "section 301", "section 232"],
    "geopolitical_risk":    ["geopolitical", "sanctions", "export control", "embargo"],
    "logistics_risk":       ["supply chain disruption", "shipping delay",
                             "port congestion", "freight disruption"],
    "semiconductor_supply": ["semiconductor", "chip shortage", "foundry", "wafer"],
    "concentration_risk":   ["geographic concentration", "customer concentration",
                             "revenue concentration"],
}

# Matches: "Apple accounted for 18% of our revenue"
# "one customer represented approximately 23% of net sales"
_CUSTOMER_PCT_RE = re.compile(
    r'([A-Z][A-Za-z0-9\s\.,\-]+?)\s+(?:accounted|represented|comprised|constituted)'
    r'\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*%\s+'
    r'(?:of\s+(?:our\s+)?(?:net\s+)?(?:revenue|sales|net sales|total revenue))',
    re.IGNORECASE,
)


def _extract_risk_flags(text: str) -> dict[str, bool]:
    """Return a dict of boolean supply-chain risk flags for a 10-K text blob."""
    text_lower = text.lower()
    return {
        flag: any(kw in text_lower for kw in keywords)
        for flag, keywords in _RISK_FLAG_PATTERNS.items()
    }


def _extract_customer_pct_mentions(text: str) -> list[dict]:
    """
    Extract customer percentage mentions from 10-K text.
    Returns list of {name, pct} dicts, deduped and sorted by pct desc.
    """
    seen: dict[str, float] = {}
    for m in _CUSTOMER_PCT_RE.finditer(text):
        name = m.group(1).strip()[:80]
        pct  = float(m.group(2)) / 100.0
        # Keep highest pct if same name appears multiple times
        if name not in seen or pct > seen[name]:
            seen[name] = pct
    return sorted(
        [{"name": k, "pct": round(v, 4)} for k, v in seen.items()],
        key=lambda x: x["pct"], reverse=True,
    )


def _get_pending_filings(limit: int | None = None) -> list[dict]:
    """Return active stocks whose 10-K text facts are missing or stale."""
    cutoff = (datetime.now() - timedelta(days=EDGAR_FILING_STALENESS)).strftime("%Y-%m-%d")
    sql = """
        SELECT s.stock_uid, s.ticker
        FROM stocks s
        WHERE s.delisted = 0
          AND NOT EXISTS (
              SELECT 1 FROM edgar_facts ef
              WHERE ef.stock_uid = s.stock_uid
                AND ef.fact_type = ?
                AND ef.fetched_at >= ?
          )
        ORDER BY s.ticker ASC
    """
    params: tuple = (FACT_RISK_FLAGS, cutoff)
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    return db.query(sql, params)


def fetch_filing_text(limit: int | None = None) -> None:
    """
    Download the latest 10-K for each pending stock via edgartools, extract
    supply-chain risk flags and customer percentage mentions, store as edgar_facts.

    edgartools installs as the 'edgar' package — same name as this file.
    We swap sys.modules['edgar'] to the real package for the entire call,
    then restore this module's entry in the finally block so nothing else breaks.
    """
    import importlib as _il
    import os as _os
    import sys as _sys

    src_dir  = _os.path.normpath(_os.path.abspath(_os.path.dirname(__file__)))
    old_path = _sys.path[:]
    old_mod  = _sys.modules.pop("edgar", None)
    _sys.path = [p for p in _sys.path
                 if _os.path.normpath(_os.path.abspath(p)) != src_dir]
    try:
        _et          = _il.import_module("edgar")
        Company      = _et.Company
        set_identity = _et.set_identity
        set_identity(EDGAR_IDENTITY)

        pending = _get_pending_filings(limit)
        if not pending:
            print("10-K filing text is up to date.")
            return

        print(f"Fetching 10-K text for {len(pending)} stocks...")
        ok = failed = skipped = 0

        for i, stock in enumerate(pending, 1):
            ticker = stock["ticker"]
            try:
                company  = Company(ticker)
                filings  = company.get_filings(form="10-K").latest(1)
                if not filings:
                    skipped += 1
                    if DEBUG_MODE:
                        print(f"[edgar] {ticker}: no 10-K found")
                    continue

                tenk        = filings.obj()
                biz_text    = str(tenk.business    or "")
                risk_text   = str(tenk.risk_factors or "")
                full_text   = biz_text + "\n" + risk_text
                fiscal_year = (tenk.period_of_report or "")[:4] or str(datetime.now().year)

                risk_flags = _extract_risk_flags(full_text)
                customers  = _extract_customer_pct_mentions(full_text)

                db.upsert_edgar_fact({
                    "stock_uid":  stock["stock_uid"],
                    "fact_type":  FACT_RISK_FLAGS,
                    "period":     fiscal_year,
                    "value_json": json.dumps(risk_flags),
                })

                if customers:
                    db.upsert_edgar_fact({
                        "stock_uid":  stock["stock_uid"],
                        "fact_type":  FACT_FILING_CUSTOMERS,
                        "period":     fiscal_year,
                        "value_json": json.dumps(customers),
                    })

                flag_count = sum(risk_flags.values())
                print(
                    f"  OK [{i}/{len(pending)}] {ticker}: "
                    f"{flag_count} risk flags, {len(customers)} customer mentions"
                )
                ok += 1

            except Exception as e:
                failed += 1
                print(f"  XX [{i}/{len(pending)}] {ticker}: {e}")

            time.sleep(EDGAR_RATE_LIMIT)

        print(f"\nDone - {ok} fetched, {skipped} no filing, {failed} failed.")

    finally:
        _sys.path = old_path
        if old_mod is not None:
            _sys.modules["edgar"] = old_mod


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_china_exposure(min_pct: float) -> None:
    rows = db.get_stocks_by_china_exposure(min_pct)
    if not rows:
        print(f"No stocks found with China revenue >= {min_pct:.0%}.")
        return
    print(f"\n{'Ticker':<8} {'China %':<10} {'Period':<8} Sector")
    print("-" * 55)
    for r in rows:
        geo = json.loads(r["value_json"])
        china_pct = geo.get("China", 0)
        print(f"  {r['ticker']:<6} {china_pct:<10.1%} {r['period']:<8} {r['sector'] or ''}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener EDGAR XBRL pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed-ciks",      action="store_true",           help="Map all tickers to SEC CIKs (run once)")
    group.add_argument("--fetch-facts",    action="store_true",           help="Pull XBRL geographic and customer facts for all stocks")
    group.add_argument("--fetch-filings",  action="store_true",           help="Download 10-K text and extract supply-chain risk flags")
    group.add_argument("--china-exposure", type=float, metavar="MIN_PCT", help="Print stocks with China revenue >= MIN_PCT (e.g. 0.15 for 15%%)")
    parser.add_argument("--limit",         type=int,   default=None, metavar="N", help="Process at most N stocks then exit")
    args = parser.parse_args()

    if args.seed_ciks:
        seed_ciks()
    elif args.fetch_facts:
        fetch_facts(args.limit)
    elif args.fetch_filings:
        fetch_filing_text(args.limit)
    elif args.china_exposure is not None:
        print_china_exposure(args.china_exposure)


if __name__ == "__main__":
    main()
