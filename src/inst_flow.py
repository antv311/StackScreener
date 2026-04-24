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
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date

import requests
import yfinance as yf

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
    EDGAR_IDENTITY,
    EDGAR_RATE_LIMIT,
    SIGNAL_OPTIONS_UNUSUAL,
    OPTIONS_CALL_SCORE,
    OPTIONS_PUT_SCORE,
    OPTIONS_VOLUME_MULT,
    OPTIONS_MIN_VOLUME,
    PROVIDER_OPTIONS,
    SIGNAL_INST_BUY,
    SIGNAL_INST_SELL,
    INST_BUY_SCORE,
    INST_SELL_SCORE,
    FORM13F_LOOKBACK_DAYS,
    PROVIDER_13F,
    INSTITUTION_CIKS,
)

_HEADERS = {"User-Agent": EDGAR_IDENTITY}

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

                accn_path  = accn.replace("-", "")
                filer_cik  = int(accn.split("-")[0])
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{filer_cik}/{accn_path}/doc4.xml"

                if db.signal_exists_by_url(PROVIDER_SEC_EDGAR, filing_url):
                    continue  # already stored from a previous run

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


# ── yfinance Options Flow ──────────────────────────────────────────────────────

def fetch_options_flow(
    tickers: list[str] | None = None,
    limit: int | None = None,
) -> int:
    """
    Scan yfinance options chains for unusual volume relative to open interest.
    Flags call volume > OPTIONS_VOLUME_MULT × OI as bullish; puts as bearish.
    Stores one signal per ticker per direction per expiration in source_signals.
    Returns count of new signals stored.
    """
    if tickers is None:
        rows = db.query(
            "SELECT stock_uid, ticker FROM stocks WHERE delisted = 0 ORDER BY market_cap DESC NULLS LAST"
        )
        if limit is not None:
            rows = rows[:limit]
        tickers_data = [(r["stock_uid"], r["ticker"]) for r in rows]
    else:
        tickers_data = []
        for t in tickers:
            stock = db.get_stock_by_ticker(t)
            if stock:
                tickers_data.append((stock["stock_uid"], t))

    if not tickers_data:
        print("No tickers to scan for options flow.")
        return 0

    print(f"Scanning options flow for {len(tickers_data)} stocks...")
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today  = datetime.now().strftime("%Y-%m-%d")
    stored = 0

    for stock_uid, ticker in tickers_data:
        try:
            tk = yf.Ticker(ticker)
            expirations = tk.options
            if not expirations:
                continue

            # Use nearest expiration only — most liquid, most signal
            chain = tk.option_chain(expirations[0])

            for direction, df, score in [
                ("call", chain.calls, OPTIONS_CALL_SCORE),
                ("put",  chain.puts,  OPTIONS_PUT_SCORE),
            ]:
                if df.empty:
                    continue

                # Flag rows where volume > mult × openInterest and meets min volume
                df = df.copy()
                df["openInterest"] = df["openInterest"].fillna(0)
                df["volume"]       = df["volume"].fillna(0)

                unusual = df[
                    (df["volume"] >= OPTIONS_MIN_VOLUME) &
                    (df["openInterest"] > 0) &
                    (df["volume"] >= OPTIONS_VOLUME_MULT * df["openInterest"])
                ]

                if unusual.empty:
                    continue

                total_vol = int(unusual["volume"].sum())
                strikes   = sorted(unusual["strike"].tolist())
                signal_url = f"yfinance://{ticker}/options/{expirations[0]}/{direction}"

                if db.signal_exists_by_url(PROVIDER_OPTIONS, signal_url):
                    continue

                reason = (
                    f"{ticker} unusual {direction} volume {total_vol:,} on {expirations[0]} "
                    f"({len(unusual)} strikes: {strikes[:3]}{'...' if len(strikes) > 3 else ''})"
                )
                db.upsert_source_signal({
                    "stock_uid":   stock_uid,
                    "source":      PROVIDER_OPTIONS,
                    "signal_type": SIGNAL_OPTIONS_UNUSUAL,
                    "sub_score":   score,
                    "reason_text": reason[:200],
                    "signal_url":  signal_url,
                    "raw_data":    json.dumps({
                        "direction":   direction,
                        "expiration":  expirations[0],
                        "total_volume": total_vol,
                        "strikes":     strikes[:10],
                    }),
                    "fetched_at":  now,
                })
                stored += 1
                if DEBUG_MODE:
                    print(f"  [options] {reason}")

        except Exception as e:
            if DEBUG_MODE:
                print(f"[options] {ticker}: {e}")

    print(f"Options flow complete: {stored} unusual signals stored.")
    return stored


# ── SEC EDGAR Form 13F — Institutional Holdings ────────────────────────────────

_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_13F_HEADERS     = {"User-Agent": "StackScreener antv311@gmail.com"}

# Normalise company names for fuzzy matching against stocks.company_name
def _norm_name(name: str) -> str:
    name = name.upper()
    # Strip common legal suffixes
    for suffix in (" INC", " CORP", " LTD", " CO", " LLC", " PLC", " SA", " NV",
                   " AG", " SE", " CLASS A", " CLASS B", " COM", " COMMON STOCK",
                   " THE", ".", ","):
        name = name.replace(suffix, "")
    return re.sub(r"\s+", " ", name).strip()


def _get_latest_13f_accession(cik: str) -> tuple[str, str] | None:
    """Return (accession_number, filing_date) for the most recent 13F-HR filing."""
    url = _SUBMISSIONS_URL.format(cik=cik)
    try:
        resp = requests.get(url, headers=_13F_HEADERS, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    recent = data.get("filings", {}).get("recent", {})
    forms  = recent.get("form", [])
    accns  = recent.get("accessionNumber", [])
    dates  = recent.get("filingDate", [])

    for form, accn, date in zip(forms, accns, dates):
        if form == "13F-HR":
            return (accn, date)
    return None


def _fetch_13f_infotable(cik: str, accession: str) -> str | None:
    """Fetch the infotable XML from a 13F-HR filing."""
    cik_int  = str(int(cik))
    accn_path = accession.replace("-", "")
    # Try standard infotable filename patterns
    for fname in ("infotable.xml", "form13fInfoTable.xml", "primary_doc.xml"):
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accn_path}/{fname}"
        try:
            resp = requests.get(url, headers=_13F_HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
    # Fall back to filing index to find the XML
    idx_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_int}&type=13F-HR&dateb=&owner=include&count=1&search_text="
    try:
        idx_resp = requests.get(
            f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accn_path}/{accn_path}-index.htm",
            headers=_13F_HEADERS, timeout=30,
        )
        if idx_resp.status_code == 200:
            match = re.search(r'href="([^"]+infotable[^"]*\.xml)"', idx_resp.text, re.IGNORECASE)
            if not match:
                match = re.search(r'href="([^"]+form13f[^"]*\.xml)"', idx_resp.text, re.IGNORECASE)
            if match:
                xml_url = "https://www.sec.gov" + match.group(1)
                xml_resp = requests.get(xml_url, headers=_13F_HEADERS, timeout=30)
                if xml_resp.status_code == 200:
                    return xml_resp.text
    except Exception:
        pass
    return None


def _parse_13f_holdings(xml_text: str) -> list[dict]:
    """Parse a 13F infotable XML. Returns list of {name, cusip, value_usd, shares}."""
    holdings = []
    try:
        # Strip namespace to simplify element access
        clean = re.sub(r'\sxmlns[^"]*"[^"]*"', "", xml_text)
        clean = re.sub(r'<[^>]+:([^>]+)>', lambda m: f"<{m.group(1)}>", clean)
        root = ET.fromstring(clean)
    except ET.ParseError:
        return []

    for entry in root.iter("infoTable"):
        name   = (entry.findtext("nameOfIssuer") or "").strip()
        cusip  = (entry.findtext("cusip") or "").strip()
        value  = entry.findtext("value") or "0"
        shares_el = entry.find("shrsOrPrnAmt")
        shares = (shares_el.findtext("sshPrnamt") if shares_el is not None else None) or "0"
        try:
            value_usd = int(value) * 1000   # SEC reports in $1,000 units
            shares    = int(shares)
        except ValueError:
            continue
        if value_usd <= 0:
            continue
        holdings.append({"name": name, "cusip": cusip, "value_usd": value_usd, "shares": shares})

    return holdings


def fetch_13f_changes(limit: int | None = None) -> int:
    """
    Fetch 13F-HR filings from configured institutional investment managers,
    compare to prior stored holdings, and store position changes as source_signals.

    Change detection: compares current holdings to prior signals stored under
    PROVIDER_13F. New / increased positions score INST_BUY_SCORE; decreased /
    exited positions score INST_SELL_SCORE.

    Returns count of new signals stored.
    """
    institutions = INSTITUTION_CIKS
    if limit is not None:
        institutions = institutions[:limit]

    # Build normalised company_name → stock lookup once
    stocks_rows = db.query(
        "SELECT stock_uid, ticker, company_name FROM stocks WHERE delisted = 0 AND company_name IS NOT NULL"
    )
    name_map: dict[str, dict] = {}
    ticker_map: dict[str, dict] = {}
    for s in stocks_rows:
        if s["company_name"]:
            name_map[_norm_name(s["company_name"])] = s
        ticker_map[s["ticker"].upper()] = s

    # Prior holdings keyed by (institution_name, ticker)
    prior_rows = db.query(
        "SELECT stock_uid, source, reason_text, raw_data FROM source_signals WHERE source = ?",
        (PROVIDER_13F,),
    )
    prior: dict[tuple[str, int], dict] = {}
    for r in prior_rows:
        try:
            rd = json.loads(r["raw_data"] or "{}")
            inst = rd.get("institution", "")
            prior[(inst, r["stock_uid"])] = rd
        except (json.JSONDecodeError, KeyError):
            pass

    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stored = 0

    for cik, inst_name in institutions:
        result = _get_latest_13f_accession(cik)
        time.sleep(EDGAR_RATE_LIMIT)
        if not result:
            if DEBUG_MODE:
                print(f"[13F] {inst_name}: no 13F-HR found")
            continue
        accn, filing_date = result

        xml_text = _fetch_13f_infotable(cik, accn)
        time.sleep(EDGAR_RATE_LIMIT)
        if not xml_text:
            if DEBUG_MODE:
                print(f"[13F] {inst_name}: infotable XML not found")
            continue

        holdings = _parse_13f_holdings(xml_text)
        if not holdings:
            continue

        print(f"  {inst_name}: {len(holdings)} positions in {filing_date} 13F")

        for h in holdings:
            # Try to match to a stock in our DB
            norm = _norm_name(h["name"])
            stock = name_map.get(norm)
            if not stock:
                # Try partial prefix match (e.g., "APPLE" matches "APPLE INC")
                for k, v in name_map.items():
                    if norm and (k.startswith(norm[:8]) or norm.startswith(k[:8])):
                        stock = v
                        break
            if not stock:
                continue

            signal_url = f"sec_13f://{cik}/{accn}/{stock['stock_uid']}"
            if db.signal_exists_by_url(PROVIDER_13F, signal_url):
                continue

            prior_holding = prior.get((inst_name, stock["stock_uid"]))
            prior_shares  = prior_holding["shares"] if prior_holding else 0

            if h["shares"] > prior_shares * 1.05:   # increased by >5%
                sig_type  = SIGNAL_INST_BUY
                sub_score = INST_BUY_SCORE
                change    = "new" if prior_shares == 0 else "increased"
            elif h["shares"] < prior_shares * 0.95: # decreased by >5%
                sig_type  = SIGNAL_INST_SELL
                sub_score = INST_SELL_SCORE
                change    = "exited" if h["shares"] == 0 else "decreased"
            else:
                continue  # no meaningful change

            value_m = h["value_usd"] / 1_000_000
            reason  = (
                f"{inst_name} {change} {stock['ticker']}: "
                f"{h['shares']:,} shares (${value_m:.1f}M) as of {filing_date}"
            )
            db.upsert_source_signal({
                "stock_uid":   stock["stock_uid"],
                "source":      PROVIDER_13F,
                "signal_type": sig_type,
                "sub_score":   sub_score,
                "reason_text": reason[:200],
                "signal_url":  signal_url,
                "raw_data":    json.dumps({
                    "institution":   inst_name,
                    "filing_date":   filing_date,
                    "shares":        h["shares"],
                    "value_usd":     h["value_usd"],
                    "change":        change,
                }),
                "fetched_at":  now,
            })
            stored += 1
            if DEBUG_MODE:
                print(f"    → {reason}")

    print(f"Form 13F complete: {stored} position change signals stored.")
    return stored


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener institutional flow ingestion")
    parser.add_argument("--senate",  action="store_true", help="Fetch Senate STOCK Act trades")
    parser.add_argument("--house",   action="store_true", help="Fetch House STOCK Act trades")
    parser.add_argument("--all",     action="store_true", help="Fetch Senate + House congressional trades")
    parser.add_argument("--form4",   action="store_true", help="Fetch SEC EDGAR Form 4 insider trades")
    parser.add_argument("--form13f", action="store_true", help="Fetch SEC EDGAR Form 13F institutional holdings")
    parser.add_argument("--options", action="store_true", help="Scan yfinance options chains for unusual volume")
    parser.add_argument("--days",    type=int, default=CONGRESS_LOOKBACK_DAYS,
                        metavar="N", help=f"Lookback window in days (default {CONGRESS_LOOKBACK_DAYS})")
    parser.add_argument("--limit",   type=int, default=None, metavar="N",
                        help="Process at most N stocks/institutions then exit")
    parser.add_argument("--tickers", nargs="+", metavar="TICKER",
                        help="--options only: scan specific tickers instead of full universe")
    args = parser.parse_args()

    db.init_db()

    if args.all:
        args.senate = args.house = True

    if not any([args.senate, args.house, args.form4, args.form13f, args.options]):
        parser.print_help()
        return

    if args.senate:
        fetch_senate_trades(args.days)
    if args.house:
        fetch_house_trades(args.days)
    if args.form4:
        fetch_form4_trades(limit=args.limit, lookback_days=args.days)
    if args.form13f:
        fetch_13f_changes(limit=args.limit)
    if args.options:
        fetch_options_flow(tickers=args.tickers, limit=args.limit)


if __name__ == "__main__":
    main()
