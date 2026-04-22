"""
news.py — News and podcast aggregator for StackScreener.

Sources:
  - WSJ podcasts        (RSS → MP3 → Whisper; uses embedded transcript if present)
  - Morgan Stanley      (RSS → MP3 → Whisper; "Thoughts on the Market")
  - Motley Fool Money   (RSS → MP3 → Whisper)
  - Yahoo Finance news  (yfinance .news — per ticker, no audio)
  - WSJ newspaper PDF   (pypdf text extraction — drop PDF in src/News/pdfs/)

Ticker mentions in all content are stored as source_signals.
Full articles/transcripts are stored in the news_articles table.

Usage:
    python src/news.py --podcasts               # all three podcast sources
    python src/news.py --yahoo AAPL MSFT NVDA   # Yahoo news for specific tickers
    python src/news.py --watchlist              # Yahoo news for all watched stocks
    python src/news.py --wsj-pdf PATH           # ingest one WSJ newspaper PDF
    python src/news.py --ingest-pdfs            # ingest all PDFs in src/News/pdfs/
    python src/news.py --all                    # podcasts + watchlist Yahoo news + pending PDFs
    python src/news.py --episodes N             # override max episodes per source (default 3)
    python src/news.py --model small            # override Whisper model size

RSS feed URLs are configured in screener_config.py. Verify them against each show's
current feed before first run (Apple Podcasts → share → copy RSS link).
"""

import argparse
import os
import re
import time
from datetime import datetime
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

import requests
import yfinance as yf

import db
from screener_config import (
    DEBUG_MODE,
    FFMPEG_BIN_DIR,
    NEWS_AUDIO_DIR,
    NEWS_PDF_DIR,
    NEWS_WHISPER_MODEL,
    NEWS_MAX_EPISODES,
    NEWS_MAX_ARTICLES,
    NEWS_TICKER_MIN_LEN,
    NEWS_TICKER_MAX_LEN,
    NEWS_SOURCE_WSJ_PODCAST,
    NEWS_SOURCE_WSJ_PDF,
    NEWS_SOURCE_MORGAN_STANLEY,
    NEWS_SOURCE_MOTLEY_FOOL,
    NEWS_SOURCE_YAHOO_FINANCE,
    NEWS_SOURCE_AP,
    NEWS_SOURCE_REUTERS,
    NEWS_SOURCE_CNBC,
    NEWS_SOURCE_MARKETWATCH,
    NEWS_SOURCE_NEWSAPI,
    NEWS_SOURCE_GDELT,
    NEWS_SIGNAL_TRANSCRIPT_MENTION,
    NEWS_SIGNAL_NEWS_HEADLINE,
    PODCAST_FEEDS,
    WSJ_PODCAST_FEEDS,
    MORGAN_STANLEY_PODCAST_FEED,
    MOTLEY_FOOL_PODCAST_FEED,
    AP_NEWS_RSS_FEEDS,
    CNBC_RSS_FEEDS,
    MARKETWATCH_RSS_FEED,
    NEWSAPI_BASE_URL,
    NEWSAPI_PAGE_SIZE,
    NEWSAPI_RATE_LIMIT,
    GDELT_BASE_URL,
    GDELT_RATE_LIMIT,
    SUPPLY_CHAIN_KEYWORDS,
    PROVIDER_NEWSAPI,
)

# Common English words and finance acronyms that look like tickers but aren't.
# Prevents false-positive signals on words like "AND", "CEO", "GDP".
_FALSE_POSITIVES: frozenset[str] = frozenset({
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "WAS",
    "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM", "HIS", "HOW", "ITS",
    "NEW", "NOW", "OLD", "SEE", "TWO", "WAY", "WHO", "DID", "LET", "PUT",
    "SAY", "SHE", "TOO", "USE", "CEO", "CFO", "COO", "CTO", "IPO", "ETF",
    "GDP", "FED", "SEC", "ESG", "USD", "EUR", "GBP", "JPY", "OTC", "LBO",
    "DCF", "EPS", "YOY", "QOQ", "FCF", "EBIT", "EBITDA", "GAAP", "AI",
    "US", "UK", "EU", "UN", "NATO", "IMF", "WTO", "OPEC", "CNBC", "CNN",
    "WSJ", "NYT", "DOW", "SPY", "VIX",
})

_TICKER_RE = re.compile(r'\b([A-Z]{2,5})\b')

# Ensure Whisper can find ffmpeg — prepend the configured bin dir to PATH.
if FFMPEG_BIN_DIR and os.path.isdir(FFMPEG_BIN_DIR):
    _path = os.environ.get("PATH", "")
    if FFMPEG_BIN_DIR not in _path:
        os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + _path

# Cached globals — loaded once per process.
_whisper_model = None
_whisper_model_name: str = NEWS_WHISPER_MODEL
_ticker_set: frozenset[str] | None = None


def set_whisper_model(name: str) -> None:
    """Override the Whisper model size. Invalidates the cached model if changed."""
    global _whisper_model, _whisper_model_name
    if _whisper_model_name != name:
        _whisper_model = None
        _whisper_model_name = name


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"  Loading Whisper model '{_whisper_model_name}'...")
        _whisper_model = whisper.load_model(_whisper_model_name)
    return _whisper_model


def _get_ticker_set() -> frozenset[str]:
    global _ticker_set
    if _ticker_set is None:
        _ticker_set = db.get_all_tickers()  # already returns frozenset
    return _ticker_set


def _ensure_dirs() -> None:
    os.makedirs(NEWS_AUDIO_DIR, exist_ok=True)
    os.makedirs(NEWS_PDF_DIR, exist_ok=True)


# ── Ticker tagging ────────────────────────────────────────────────────────────

def _tag_tickers(text: str) -> list[str]:
    """Return deduplicated list of real tickers mentioned in text."""
    ticker_set = _get_ticker_set()
    found = _TICKER_RE.findall(text)
    seen: dict[str, None] = {}
    for t in found:
        if (
            t in ticker_set
            and t not in _FALSE_POSITIVES
            and NEWS_TICKER_MIN_LEN <= len(t) <= NEWS_TICKER_MAX_LEN
        ):
            seen[t] = None
    return list(seen)


def _store_ticker_signals(
    tickers: list[str],
    source: str,
    signal_type: str,
    reason_prefix: str,
    url: str | None,
) -> None:
    if not tickers:
        return
    stock_map = db.get_stocks_by_tickers(tickers)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ticker in tickers:
        stock = stock_map.get(ticker)
        if not stock:
            continue
        db.upsert_source_signal({
            "stock_uid":   stock["stock_uid"],
            "source":      source,
            "signal_type": signal_type,
            "reason_text": f"{reason_prefix}: {ticker}",
            "signal_url":  url,
            "fetched_at":  now,
        })


# ── RSS + audio pipeline ──────────────────────────────────────────────────────

def _parse_rss(feed_url: str) -> list[dict]:
    """Fetch and parse an RSS feed. Returns list of episode dicts."""
    resp = requests.get(
        feed_url, timeout=20,
        headers={"User-Agent": "StackScreener/1.0 (news aggregator)"},
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    episodes: list[dict] = []
    for item in root.findall(".//item"):
        enclosure = item.find("enclosure")
        if enclosure is None:
            continue
        # Check for embedded transcript tag (podcast:transcript — Apple/RSS standard)
        transcript_url = None
        for child in item:
            if child.tag.lower().endswith("transcript"):
                transcript_url = child.get("url")
                break
        episodes.append({
            "title":          (item.findtext("title") or "").strip(),
            "audio_url":      enclosure.get("url", ""),
            "published":      item.findtext("pubDate") or "",
            "description":    (item.findtext("description") or "")[:500],
            "transcript_url": transcript_url,
        })
    return episodes


def _fetch_transcript_url(url: str) -> str | None:
    """Fetch a transcript from a direct URL (SRT / VTT / JSON / plain text)."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            import json
            data = json.loads(resp.text)
            # Podcast Index JSON transcript format
            if isinstance(data, dict) and "segments" in data:
                return " ".join(s.get("body", "") for s in data["segments"])
            # Generic text field
            return str(data)
        return resp.text
    except Exception:
        return None


def _download_audio(url: str) -> str:
    """Stream an MP3 to NEWS_AUDIO_DIR. Returns local file path."""
    _ensure_dirs()
    fname = os.path.basename(url.split("?")[0]) or "episode.mp3"
    dest = os.path.join(NEWS_AUDIO_DIR, fname)
    resp = requests.get(url, stream=True, timeout=120,
                        headers={"User-Agent": "StackScreener/1.0 (podcast aggregator)"})
    resp.raise_for_status()
    ct = resp.headers.get("content-type", "")
    if "html" in ct or "xml" in ct:
        raise ValueError(f"Expected audio, got {ct} — feed may require authentication")
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=131_072):
            fh.write(chunk)
    return dest


def _transcribe_and_delete(audio_path: str) -> str:
    """Transcribe audio with Whisper then delete the file. Returns transcript text."""
    try:
        result = _get_whisper_model().transcribe(audio_path)
        return result["text"]
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


def _process_podcast(
    feed_url: str,
    source_name: str,
    max_episodes: int,
) -> int:
    """Fetch RSS, transcribe each episode, store article + ticker signals."""
    if not feed_url:
        print(f"  [{source_name}] no feed URL configured — skipping")
        return 0

    try:
        episodes = _parse_rss(feed_url)[:max_episodes]
    except Exception as e:
        print(f"  [{source_name}] RSS fetch failed: {e}")
        return 0

    stored = 0
    for ep in episodes:
        if not ep["audio_url"]:
            continue

        text: str | None = None

        # Prefer embedded transcript — avoids downloading audio entirely
        if ep["transcript_url"]:
            text = _fetch_transcript_url(ep["transcript_url"])
            if text and DEBUG_MODE:
                print(f"  [{source_name}] used embedded transcript: {ep['title']}")

        # Fall back to Whisper transcription
        if not text:
            try:
                audio_path = _download_audio(ep["audio_url"])
                text = _transcribe_and_delete(audio_path)
            except Exception as e:
                print(f"  [{source_name}] transcription failed — {ep['title']}: {e}")
                continue

        tickers = _tag_tickers(text)

        db.upsert_news_article({
            "source":       source_name,
            "headline":     ep["title"],
            "summary":      ep["description"] or None,
            "body":         text,
            "url":          ep["audio_url"],
            "published_at": ep["published"] or None,
        })

        _store_ticker_signals(
            tickers, source_name, NEWS_SIGNAL_TRANSCRIPT_MENTION,
            f"Mentioned in '{ep['title']}'", ep["audio_url"],
        )

        print(f"  OK [{source_name}] {ep['title']} — {len(tickers)} tickers tagged")
        stored += 1

    return stored


# ── Source-specific fetchers ──────────────────────────────────────────────────

def fetch_wsj_podcasts(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    """Fetch all configured WSJ podcast feeds, reading URLs from settings table."""
    feed_1 = db.get_setting(1, "wsj_podcast_feed_1") or (WSJ_PODCAST_FEEDS[0] if WSJ_PODCAST_FEEDS else "")
    feed_2 = db.get_setting(1, "wsj_podcast_feed_2") or (WSJ_PODCAST_FEEDS[1] if len(WSJ_PODCAST_FEEDS) > 1 else "")
    total = 0
    for url in filter(None, [feed_1, feed_2]):
        total += _process_podcast(url, NEWS_SOURCE_WSJ_PODCAST, max_episodes)
    return total


def fetch_morgan_stanley(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    url = db.get_setting(1, "morgan_stanley_feed") or MORGAN_STANLEY_PODCAST_FEED
    return _process_podcast(url, NEWS_SOURCE_MORGAN_STANLEY, max_episodes)


def fetch_motley_fool(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    url = db.get_setting(1, "motley_fool_feed") or MOTLEY_FOOL_PODCAST_FEED
    return _process_podcast(url, NEWS_SOURCE_MOTLEY_FOOL, max_episodes)


def fetch_all_podcasts(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    """
    Process every feed in PODCAST_FEEDS. Settings-table overrides apply to the
    legacy single-feed keys (wsj_podcast_feed_1/2, morgan_stanley_feed,
    motley_fool_feed) — all other feeds use the config URL directly.
    """
    # Build overrides from the settings table for the 4 legacy keys
    overrides: dict[str, str] = {}
    for setting_key, feed_url in [
        ("wsj_podcast_feed_1",  WSJ_PODCAST_FEEDS[0] if WSJ_PODCAST_FEEDS else ""),
        ("wsj_podcast_feed_2",  WSJ_PODCAST_FEEDS[1] if len(WSJ_PODCAST_FEEDS) > 1 else ""),
        ("morgan_stanley_feed", MORGAN_STANLEY_PODCAST_FEED),
        ("motley_fool_feed",    MOTLEY_FOOL_PODCAST_FEED),
    ]:
        saved = db.get_setting(1, setting_key)
        if saved:
            overrides[feed_url] = saved  # keyed by default URL so we can remap below

    total = 0
    for source, url in PODCAST_FEEDS:
        effective_url = overrides.get(url, url)  # use settings override if present
        if not effective_url:
            continue
        n = _process_podcast(effective_url, source, max_episodes)
        total += n
    return total


def fetch_yahoo_news(tickers: list[str]) -> int:
    """Fetch Yahoo Finance news for a list of tickers. No audio involved."""
    stored = 0
    ticker_set = _get_ticker_set()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sym in tickers:
        try:
            items = yf.Ticker(sym).news or []
            stock = db.get_stock_by_ticker(sym)
            for item in items:
                headline = item.get("title") or ""
                url      = item.get("link") or ""
                pub_ts   = item.get("providerPublishTime")
                pub_str  = (
                    datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M:%S")
                    if pub_ts else None
                )

                db.upsert_news_article({
                    "stock_uid":    stock["stock_uid"] if stock else None,
                    "source":       NEWS_SOURCE_YAHOO_FINANCE,
                    "headline":     headline,
                    "url":          url,
                    "published_at": pub_str,
                })

                if stock and headline:
                    db.upsert_source_signal({
                        "stock_uid":   stock["stock_uid"],
                        "source":      NEWS_SOURCE_YAHOO_FINANCE,
                        "signal_type": NEWS_SIGNAL_NEWS_HEADLINE,
                        "reason_text": headline[:200],
                        "signal_url":  url,
                        "fetched_at":  now,
                    })
                stored += 1

            if DEBUG_MODE:
                print(f"  [{NEWS_SOURCE_YAHOO_FINANCE}] {sym}: {len(items)} items")
        except Exception as e:
            print(f"  [{NEWS_SOURCE_YAHOO_FINANCE}] {sym} failed: {e}")

    return stored


def fetch_watchlist_yahoo_news() -> int:
    """Fetch Yahoo Finance news for all stocks currently on a watchlist."""
    tickers = db.get_watched_tickers()
    if not tickers:
        print("  No watchlist stocks found.")
        return 0
    print(f"  Fetching Yahoo news for {len(tickers)} watchlist stocks...")
    return fetch_yahoo_news(tickers)


# ── WSJ PDF pipeline ──────────────────────────────────────────────────────────

def ingest_wsj_pdf(pdf_path: str) -> int:
    """Extract text from a WSJ newspaper PDF, tag tickers, store in news_articles."""
    from pypdf import PdfReader

    print(f"  Ingesting: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"  PDF read failed: {e}")
        return 0

    tickers = _tag_tickers(full_text)
    date_str = datetime.now().strftime("%Y-%m-%d")
    headline = f"WSJ Newspaper — {date_str}"
    abs_path = os.path.abspath(pdf_path)

    db.upsert_news_article({
        "source":       NEWS_SOURCE_WSJ_PDF,
        "headline":     headline,
        "body":         full_text,
        "url":          abs_path,
        "published_at": date_str,
    })

    _store_ticker_signals(
        tickers, NEWS_SOURCE_WSJ_PDF, NEWS_SIGNAL_NEWS_HEADLINE,
        f"Mentioned in WSJ newspaper {date_str}", abs_path,
    )

    print(f"  OK {headline} — {len(full_text):,} chars, {len(tickers)} tickers tagged")
    return 1


def ingest_pending_pdfs() -> int:
    """Ingest all PDFs sitting in NEWS_PDF_DIR that haven't been ingested yet."""
    _ensure_dirs()
    pdf_files = [f for f in os.listdir(NEWS_PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"  No PDFs found in {NEWS_PDF_DIR}")
        return 0

    already_ingested = db.get_news_article_urls(NEWS_SOURCE_WSJ_PDF)
    total = 0
    for fname in sorted(pdf_files):
        abs_path = os.path.abspath(os.path.join(NEWS_PDF_DIR, fname))
        if abs_path in already_ingested:
            if DEBUG_MODE:
                print(f"  [{fname}] already ingested, skipping")
            continue
        total += ingest_wsj_pdf(abs_path)

    return total


# ── Article RSS pipeline (no audio) ──────────────────────────────────────────

def _parse_article_rss(feed_url: str, max_items: int) -> list[dict]:
    """Fetch and parse an article RSS feed (no audio enclosure required)."""
    resp = requests.get(
        feed_url, timeout=20,
        headers={"User-Agent": "StackScreener/1.0 (news aggregator)"},
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    articles: list[dict] = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link  = item.findtext("link") or ""
        desc  = (item.findtext("description") or "")[:1000]
        pub   = item.findtext("pubDate") or ""
        if title and link:
            articles.append({"title": title, "url": link, "description": desc, "published": pub})
    return articles


def _ingest_rss_articles(
    feed_url: str,
    source_name: str,
    max_articles: int = NEWS_MAX_ARTICLES,
) -> int:
    """Fetch an article RSS feed, tag tickers, store deduplicated rows."""
    try:
        items = _parse_article_rss(feed_url, max_articles)
    except Exception as e:
        print(f"  [{source_name}] RSS fetch failed ({feed_url}): {e}")
        return 0

    existing = db.get_news_article_urls(source_name)
    stored = 0
    for item in items:
        if item["url"] in existing:
            continue
        text = f"{item['title']} {item['description']}"
        tickers = _tag_tickers(text)
        db.upsert_news_article({
            "source":       source_name,
            "headline":     item["title"],
            "summary":      item["description"] or None,
            "url":          item["url"],
            "published_at": item["published"] or None,
        })
        _store_ticker_signals(
            tickers, source_name, NEWS_SIGNAL_NEWS_HEADLINE,
            f"Mentioned in '{item['title']}'", item["url"],
        )
        stored += 1

    if stored:
        print(f"  [{source_name}] {stored} new articles")
    return stored


def fetch_ap_news(max_articles: int = NEWS_MAX_ARTICLES) -> int:
    """Fetch AP News RSS feeds (business, finance, technology)."""
    total = 0
    for _label, url in AP_NEWS_RSS_FEEDS:
        total += _ingest_rss_articles(url, NEWS_SOURCE_AP, max_articles)
    return total


def fetch_cnbc_news(max_articles: int = NEWS_MAX_ARTICLES) -> int:
    """Fetch CNBC RSS feeds (US business, finance)."""
    total = 0
    for _label, url in CNBC_RSS_FEEDS:
        total += _ingest_rss_articles(url, NEWS_SOURCE_CNBC, max_articles)
    return total


def fetch_marketwatch_news(max_articles: int = NEWS_MAX_ARTICLES) -> int:
    """Fetch MarketWatch top stories RSS feed."""
    return _ingest_rss_articles(MARKETWATCH_RSS_FEED, NEWS_SOURCE_MARKETWATCH, max_articles)


# ── NewsAPI.org pipeline ──────────────────────────────────────────────────────

def _fetch_newsapi_articles(
    query: str,
    api_key: str,
    source_name: str,
    domains: str | None = None,
    max_articles: int = NEWSAPI_PAGE_SIZE,
) -> int:
    """Core NewsAPI helper. `domains` filters to a comma-separated list of domains."""
    params: dict = {
        "q":        query,
        "apiKey":   api_key,
        "pageSize": min(max_articles, 100),
        "language": "en",
        "sortBy":   "publishedAt",
    }
    if domains:
        params["domains"] = domains

    try:
        resp = requests.get(NEWSAPI_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [{source_name}] NewsAPI request failed: {e}")
        return 0

    articles = data.get("articles") or []
    existing = db.get_news_article_urls(source_name)
    stored = 0
    for art in articles:
        url = art.get("url") or ""
        if not url or url in existing:
            continue
        title   = (art.get("title") or "").strip()
        desc    = (art.get("description") or "")[:1000]
        body    = (art.get("content") or "")[:2000]
        pub_str = art.get("publishedAt") or None

        tickers = _tag_tickers(f"{title} {desc} {body}")
        db.upsert_news_article({
            "source":       source_name,
            "headline":     title,
            "summary":      desc or None,
            "body":         body or None,
            "url":          url,
            "published_at": pub_str,
        })
        _store_ticker_signals(
            tickers, source_name, NEWS_SIGNAL_NEWS_HEADLINE,
            f"Mentioned in '{title}'", url,
        )
        time.sleep(NEWSAPI_RATE_LIMIT)
        stored += 1

    if stored:
        print(f"  [{source_name}] {stored} new articles for '{query}'")
    return stored


def fetch_newsapi(query: str, user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Fetch NewsAPI.org results for a keyword query (150k+ sources, AP, Reuters included)."""
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [newsapi] No API key. Store with: db.set_api_key(1, 'newsapi', 'YOUR_KEY')")
        return 0
    return _fetch_newsapi_articles(query, api_key, NEWS_SOURCE_NEWSAPI,
                                   max_articles=max_articles)


def fetch_reuters(user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Fetch Reuters content via NewsAPI (Reuters discontinued public RSS in 2023)."""
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [reuters] NewsAPI key required. Store with: db.set_api_key(1, 'newsapi', 'YOUR_KEY')")
        return 0
    query = "supply chain OR commodity OR logistics OR sanctions OR trade"
    return _fetch_newsapi_articles(query, api_key, NEWS_SOURCE_REUTERS,
                                   domains="reuters.com", max_articles=max_articles)


# ── GDELT pipeline ────────────────────────────────────────────────────────────

def fetch_gdelt(keywords: list[str], max_records: int = 25) -> int:
    """Fetch GDELT global event articles matching keywords. Free, no key required."""
    query = " ".join(keywords)
    params: dict = {
        "query":      query,
        "mode":       "artlist",
        "maxrecords": max_records,
        "format":     "json",
    }
    try:
        time.sleep(GDELT_RATE_LIMIT)
        resp = requests.get(GDELT_BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [gdelt] Request failed: {e}")
        return 0

    articles = data.get("articles") or []
    existing = db.get_news_article_urls(NEWS_SOURCE_GDELT)
    stored = 0
    for art in articles:
        url = art.get("url") or ""
        if not url or url in existing:
            continue
        title    = (art.get("title") or "").strip()
        domain   = art.get("domain") or ""
        seendate = art.get("seendate") or ""

        pub_str: str | None = None
        if seendate and len(seendate) >= 15:
            try:
                pub_str = datetime.strptime(seendate[:15], "%Y%m%dT%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        tickers = _tag_tickers(f"{title} {domain}")
        db.upsert_news_article({
            "source":       NEWS_SOURCE_GDELT,
            "headline":     title,
            "summary":      f"Source: {domain}" if domain else None,
            "url":          url,
            "published_at": pub_str,
        })
        _store_ticker_signals(
            tickers, NEWS_SOURCE_GDELT, NEWS_SIGNAL_NEWS_HEADLINE,
            f"Mentioned in '{title}'", url,
        )
        stored += 1

    if stored:
        print(f"  [gdelt] {stored} new articles for '{query}'")
    return stored


# ── Entry point ───────────────────────────────────────────────────────────────

def run(
    podcasts:       bool = False,
    yahoo_tickers:  list[str] | None = None,
    watchlist:      bool = False,
    wsj_pdf:        str | None = None,
    ingest_pdfs:    bool = False,
    ap:             bool = False,
    cnbc:           bool = False,
    marketwatch:    bool = False,
    reuters:        bool = False,
    newsapi_query:  str | None = None,
    gdelt_keywords: list[str] | None = None,
    all_sources:    bool = False,
    max_episodes:   int = NEWS_MAX_EPISODES,
    max_articles:   int = NEWS_MAX_ARTICLES,
    whisper_model:  str | None = None,
    user_uid:       int = 1,
) -> None:
    if whisper_model:
        set_whisper_model(whisper_model)

    db.init_db()
    _ensure_dirs()

    if all_sources:
        podcasts    = True
        watchlist   = True
        ingest_pdfs = True
        ap          = True
        cnbc        = True
        marketwatch = True

    if podcasts:
        print("-- Podcasts (all sources) -----------------------")
        n = fetch_all_podcasts(max_episodes)
        print(f"   {n} episodes stored\n")

    if yahoo_tickers:
        print("-- Yahoo Finance News ---------------------------")
        n = fetch_yahoo_news(yahoo_tickers)
        print(f"   {n} articles stored\n")

    if watchlist:
        print("-- Yahoo Finance - Watchlist --------------------")
        n = fetch_watchlist_yahoo_news()
        print(f"   {n} articles stored\n")

    if wsj_pdf:
        print("-- WSJ PDF --------------------------------------")
        ingest_wsj_pdf(wsj_pdf)
        print()

    if ingest_pdfs:
        print("-- WSJ PDF Directory ----------------------------")
        n = ingest_pending_pdfs()
        print(f"   {n} PDFs ingested\n")

    if ap:
        print("-- AP News RSS ----------------------------------")
        n = fetch_ap_news(max_articles)
        print(f"   {n} new articles\n")

    if cnbc:
        print("-- CNBC RSS -------------------------------------")
        n = fetch_cnbc_news(max_articles)
        print(f"   {n} new articles\n")

    if marketwatch:
        print("-- MarketWatch RSS ------------------------------")
        n = fetch_marketwatch_news(max_articles)
        print(f"   {n} new articles\n")

    if reuters:
        print("-- Reuters (via NewsAPI) ------------------------")
        n = fetch_reuters(user_uid=user_uid, max_articles=max_articles)
        print(f"   {n} new articles\n")

    if newsapi_query:
        print(f"-- NewsAPI: '{newsapi_query}' -------------------")
        n = fetch_newsapi(newsapi_query, user_uid=user_uid, max_articles=max_articles)
        print(f"   {n} new articles\n")

    if gdelt_keywords:
        print(f"-- GDELT: {gdelt_keywords} ----------------------")
        n = fetch_gdelt(gdelt_keywords)
        print(f"   {n} new articles\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener news aggregator")
    parser.add_argument("--podcasts",     action="store_true",         help="Fetch all podcast sources (WSJ, Morgan Stanley, Motley Fool)")
    parser.add_argument("--yahoo",        nargs="+", metavar="TICKER", help="Fetch Yahoo Finance news for specific tickers")
    parser.add_argument("--watchlist",    action="store_true",         help="Fetch Yahoo Finance news for all watchlist stocks")
    parser.add_argument("--wsj-pdf",      metavar="PATH",              help="Ingest a specific WSJ newspaper PDF")
    parser.add_argument("--ingest-pdfs",  action="store_true",         help=f"Ingest all new PDFs in {NEWS_PDF_DIR}")
    parser.add_argument("--ap",           action="store_true",         help="Fetch AP News RSS (business + finance + technology)")
    parser.add_argument("--cnbc",         action="store_true",         help="Fetch CNBC RSS feeds")
    parser.add_argument("--marketwatch",  action="store_true",         help="Fetch MarketWatch RSS top stories")
    parser.add_argument("--reuters",      action="store_true",         help="Fetch Reuters via NewsAPI (requires newsapi key)")
    parser.add_argument("--newsapi",      metavar="QUERY",             help="Fetch NewsAPI.org results for a keyword query")
    parser.add_argument("--gdelt",        nargs="+", metavar="KEYWORD", help="Fetch GDELT global event articles matching keywords")
    parser.add_argument("--all",          action="store_true",         help="Run all free sources (podcasts + watchlist + PDFs + AP + CNBC + MarketWatch)")
    parser.add_argument("--episodes",     type=int, default=NEWS_MAX_EPISODES,  metavar="N", help=f"Max episodes per podcast source (default {NEWS_MAX_EPISODES})")
    parser.add_argument("--articles",     type=int, default=NEWS_MAX_ARTICLES,  metavar="N", help=f"Max articles per news source (default {NEWS_MAX_ARTICLES})")
    parser.add_argument("--model",        default=None, metavar="SIZE", help="Whisper model size: base | small | medium | large")
    args = parser.parse_args()

    run(
        podcasts=args.podcasts,
        yahoo_tickers=args.yahoo,
        watchlist=args.watchlist,
        wsj_pdf=args.wsj_pdf,
        ingest_pdfs=args.ingest_pdfs,
        ap=args.ap,
        cnbc=args.cnbc,
        marketwatch=args.marketwatch,
        reuters=args.reuters,
        newsapi_query=args.newsapi,
        gdelt_keywords=args.gdelt,
        all_sources=args.all,
        max_episodes=args.episodes,
        max_articles=args.articles,
        whisper_model=args.model,
    )


if __name__ == "__main__":
    main()
