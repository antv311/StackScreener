"""
inst_flow.py — Institutional flow ingestion for StackScreener.

Sources (all free, no API key required):
  - Senate Stock Watcher  https://senatestockwatcher.com/api
  - House Stock Watcher   https://housestockwatcher.com/api
  - SEC EDGAR Form 4      https://efts.sec.gov/LATEST/search-index (insider trades)

Trades are stored in source_signals. Congressional purchases score CONGRESS_BUY_SCORE,
insider buys score INSIDER_BUY_SCORE.

Usage:
    python src/inst_flow.py --senate
    python src/inst_flow.py --house
    python src/inst_flow.py --all
    python src/inst_flow.py --all --days 90     # only pull last N days
    python src/inst_flow.py --form4             # SEC EDGAR Form 4 insider trades
    python src/inst_flow.py --form4 --limit 200 # process N stocks only
"""

import argparse
import json
import time
import xml.etree.ElementTree as ET
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
    SIGNAL_INSIDER_BUY,
    SIGNAL_INSIDER_SELL,
    INSIDER_BUY_SCORE,
    INSIDER_SELL_SCORE,
    FORM4_LOOKBACK_DAYS,
    PROVIDER_SEC_EDGAR,
    EDGAR_RATE_LIMIT,
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


# ── SEC EDGAR Form 4 — Insider Trades ─────────────────────────────────────────

_EDGAR_HEADERS    = {"User-Agent": "StackScreener antv311@gmail.com"}
_EFTS_SEARCH_URL  = "https://efts.sec.gov/LATEST/search-index"
_FORM4_XML_NS     = ""   # Form 4 XML has no namespace

# Transaction codes per SEC rules (ownershipDocument/nonDerivativeTransaction)
_FORM4_BUY_CODES  = frozenset({"A"})   # A = Acquired
_FORM4_SELL_CODES = frozenset({"D"})   # D = Disposed


def _xml_text(element: ET.Element | None) -> str:
    """Safe text extraction from an XML element."""
    if element is None:
        return ""
    return (element.text or "").strip()


def _search_form4_accessions(ticker: str, start_date: str, end_date: str) -> list[str]:
    """
    Use EDGAR full-text search to find Form 4 accession numbers filed for a ticker.
    Returns list of accession numbers (e.g. '0001234567-26-012345').
    """
    params = {
        "q":          f'"{ticker}"',
        "forms":      "4",
        "dateRange":  "custom",
        "startdt":    start_date,
        "enddt":      end_date,
        "_source":    "period_of_report,entity_name,file_num",
        "hits.hits.total.value": "true",
    }
    try:
        resp = requests.get(_EFTS_SEARCH_URL, params=params, headers=_EDGAR_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        if DEBUG_MODE:
            print(f"[form4] EFTS search failed for {ticker}: {e}")
        return []

    hits = data.get("hits", {}).get("hits", [])
    return [h["_id"] for h in hits if "_id" in h]


def _fetch_form4_xml(accession: str) -> str | None:
    """
    Fetch the Form 4 XML document for a given accession number.
    EDGAR accession format: 0001234567-26-012345
    """
    accn_path = accession.replace("-", "")
    # Filer CIK is the first 10 digits of the accession number
    filer_cik = accession.split("-")[0]
    url = f"https://www.sec.gov/Archives/edgar/data/{int(filer_cik)}/{accn_path}/doc4.xml"
    try:
        resp = requests.get(url, headers=_EDGAR_HEADERS, timeout=30)
        if resp.status_code == 404:
            # Try the filing index to find the actual XML filename
            index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum=&State=0&SIC=&dateb=&owner=include&count=1&search_text=&action=getcompany"
            # Fall back to accession-based index
            idx_url = f"https://www.sec.gov/Archives/edgar/data/{int(filer_cik)}/{accn_path}/{accn_path}-index.htm"
            idx_resp = requests.get(idx_url, headers=_EDGAR_HEADERS, timeout=30)
            if idx_resp.status_code != 200:
                return None
            # Find the .xml link in the index
            import re as _re
            match = _re.search(r'href="([^"]+\.xml)"', idx_resp.text, _re.IGNORECASE)
            if not match:
                return None
            xml_url = "https://www.sec.gov" + match.group(1)
            xml_resp = requests.get(xml_url, headers=_EDGAR_HEADERS, timeout=30)
            if xml_resp.status_code != 200:
                return None
            return xml_resp.text
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        if DEBUG_MODE:
            print(f"[form4] XML fetch failed for {accession}: {e}")
        return None


def _parse_form4_transactions(xml_text: str) -> list[dict]:
    """
    Parse a Form 4 XML document and return a list of non-derivative transactions.
    Each dict: {ticker, transaction_date, code, shares, price, insider_name, insider_title}
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    issuer_ticker = _xml_text(root.find(".//issuerTradingSymbol")).upper()

    # Insider identity
    owner_el = root.find(".//reportingOwner")
    if owner_el is not None:
        name_el = owner_el.find(".//rptOwnerName")
        rel_el  = owner_el.find(".//reportingOwnerRelationship")
        insider_name  = _xml_text(name_el)
        title_parts = []
        if rel_el is not None:
            if _xml_text(rel_el.find("isDirector")) == "1":
                title_parts.append("Director")
            if _xml_text(rel_el.find("isOfficer")) == "1":
                title_parts.append(_xml_text(rel_el.find("officerTitle")) or "Officer")
            if _xml_text(rel_el.find("isTenPercentOwner")) == "1":
                title_parts.append("10% Owner")
        insider_title = ", ".join(title_parts) or "Insider"
    else:
        insider_name  = "Unknown"
        insider_title = "Insider"

    transactions = []
    for tx in root.findall(".//nonDerivativeTransaction"):
        code   = _xml_text(tx.find(".//transactionAcquiredDisposedCode/value"))
        shares_text = _xml_text(tx.find(".//transactionShares/value"))
        price_text  = _xml_text(tx.find(".//transactionPricePerShare/value"))
        date_text   = _xml_text(tx.find(".//transactionDate/value"))

        if code not in (_FORM4_BUY_CODES | _FORM4_SELL_CODES):
            continue
        try:
            shares = float(shares_text) if shares_text else 0.0
            price  = float(price_text)  if price_text  else 0.0
        except ValueError:
            continue
        if shares <= 0:
            continue

        transactions.append({
            "ticker":        issuer_ticker,
            "transaction_date": date_text,
            "code":          code,
            "shares":        shares,
            "price":         price,
            "insider_name":  insider_name,
            "insider_title": insider_title,
        })

    return transactions


def fetch_form4_trades(
    limit: int | None = None,
    lookback_days: int = FORM4_LOOKBACK_DAYS,
) -> int:
    """
    Fetch recent Form 4 insider trade filings for all active stocks (with CIKs).
    Stores BUY/SELL signals in source_signals. Returns count of new signals stored.
    """
    stocks = db.query(
        "SELECT stock_uid, ticker, cik FROM stocks WHERE cik IS NOT NULL AND delisted = 0 ORDER BY ticker"
    )
    if limit is not None:
        stocks = stocks[:limit]

    if not stocks:
        print("No stocks with CIKs found.")
        return 0

    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end_date   = datetime.now().strftime("%Y-%m-%d")
    now        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stored     = 0

    print(f"Fetching Form 4 insider trades for {len(stocks)} stocks (last {lookback_days} days)...")

    for i, stock in enumerate(stocks, 1):
        accessions = _search_form4_accessions(stock["ticker"], start_date, end_date)
        time.sleep(EDGAR_RATE_LIMIT)

        if not accessions:
            continue

        for accn in accessions[:5]:  # cap at 5 filings per ticker per run
            xml_text = _fetch_form4_xml(accn)
            time.sleep(EDGAR_RATE_LIMIT)
            if not xml_text:
                continue

            transactions = _parse_form4_transactions(xml_text)
            for tx in transactions:
                if tx["ticker"] != stock["ticker"].upper():
                    continue  # EFTS search can return close matches — verify ticker

                sig_type = SIGNAL_INSIDER_BUY if tx["code"] in _FORM4_BUY_CODES else SIGNAL_INSIDER_SELL
                sub_score = INSIDER_BUY_SCORE if sig_type == SIGNAL_INSIDER_BUY else INSIDER_SELL_SCORE

                accn_path = accn.replace("-", "")
                filer_cik = int(accn.split("-")[0])
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{filer_cik}/{accn_path}/doc4.xml"

                action = "bought" if sig_type == SIGNAL_INSIDER_BUY else "sold"
                value  = tx["shares"] * tx["price"]
                reason = (
                    f"{tx['insider_name']} ({tx['insider_title']}) {action} "
                    f"{tx['shares']:,.0f} shares @ ${tx['price']:.2f} "
                    f"(${value:,.0f}) on {tx['transaction_date']}"
                )

                db.upsert_source_signal({
                    "stock_uid":   stock["stock_uid"],
                    "source":      PROVIDER_SEC_EDGAR,
                    "signal_type": sig_type,
                    "sub_score":   sub_score,
                    "reason_text": reason[:200],
                    "signal_url":  filing_url,
                    "raw_data":    json.dumps(tx),
                    "fetched_at":  now,
                })
                stored += 1
                if DEBUG_MODE:
                    print(f"  [form4] {stock['ticker']}: {reason}")

        if i % 50 == 0:
            print(f"  Progress: {i}/{len(stocks)} stocks, {stored} signals stored so far")

    print(f"Form 4 complete: {stored} new insider trade signals stored.")
    return stored


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener institutional flow ingestion")
    parser.add_argument("--senate", action="store_true", help="Fetch Senate STOCK Act trades")
    parser.add_argument("--house",  action="store_true", help="Fetch House STOCK Act trades")
    parser.add_argument("--all",    action="store_true", help="Fetch both Senate and House trades")
    parser.add_argument("--form4",  action="store_true", help="Fetch SEC EDGAR Form 4 insider trades")
    parser.add_argument("--days",   type=int, default=CONGRESS_LOOKBACK_DAYS,
                        metavar="N", help=f"Lookback window in days (default {CONGRESS_LOOKBACK_DAYS})")
    parser.add_argument("--limit",  type=int, default=None, metavar="N",
                        help="Form 4 only: process at most N stocks then exit")
    args = parser.parse_args()

    db.init_db()

    if args.all:
        args.senate = args.house = True

    if not any([args.senate, args.house, args.form4]):
        parser.print_help()
        return

    if args.senate:
        fetch_senate_trades(args.days)
    if args.house:
        fetch_house_trades(args.days)
    if args.form4:
        fetch_form4_trades(limit=args.limit, lookback_days=args.days)


if __name__ == "__main__":
    main()
