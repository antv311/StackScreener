"""
news.py — News and podcast aggregator for StackScreener.

Sources:
  - WSJ podcasts        (RSS → MP3 → Whisper; uses embedded transcript if present)
  - Morgan Stanley      (RSS → MP3 → Whisper; "Thoughts on the Market")
  - Motley Fool Money   (RSS → MP3 → Whisper)
  - Yahoo Finance news  (yfinance .news — per ticker, no audio)
  - WSJ newspaper PDF   (pypdf text extraction — drop PDF in src/News/pdfs/)
  - AP News RSS, CNBC RSS, MarketWatch RSS
  - NewsAPI.org REST (AP, Reuters + 150k sources; requires key)
  - GDELT Project REST (global event database; free, no key)

Ticker mentions in all content are stored as source_signals.
Full articles/transcripts are stored in the news_articles table.

LLM post-ingest hook:
  - --classify  Run the LLM disruption classifier on unclassified news_articles rows.
                Articles with is_supply_chain=True and confidence >= threshold are
                promoted to supply_chain_events candidates.

Usage:
    python src/news.py --podcasts               # all three podcast sources
    python src/news.py --yahoo AAPL MSFT NVDA   # Yahoo news for specific tickers
    python src/news.py --watchlist              # Yahoo news for all watched stocks
    python src/news.py --wsj-pdf PATH           # ingest one WSJ newspaper PDF
    python src/news.py --ingest-pdfs            # ingest all PDFs in src/News/pdfs/
    python src/news.py --ap                     # AP News RSS
    python src/news.py --cnbc                   # CNBC RSS
    python src/news.py --marketwatch            # MarketWatch RSS
    python src/news.py --reuters                # Reuters via NewsAPI (requires key)
    python src/news.py --newsapi "supply chain" # NewsAPI keyword query
    python src/news.py --gdelt supply chain fire # GDELT event search
    python src/news.py --all                    # all free sources
    python src/news.py --classify               # run LLM classifier on unclassified rows
    python src/news.py --classify --limit 20    # classify at most 20 articles
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
    NEWSAPI_SOURCES_URL,
    NEWSAPI_MAX_SOURCES_PER_CALL,
    NEWSAPI_DEFAULT_KEYWORDS,
    ROLE_NEWS_CONNECTOR,
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
    LLM_CLASSIFY_CONFIDENCE_THRESHOLD,
    EVENT_STATUS_MONITORING,
    SEVERITY_MEDIUM, SEVERITY_HIGH,
    CONFIDENCE_MEDIUM,
    ROLE_IMPACTED,
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
_ticker_set_loaded_at: float = 0.0
_TICKER_SET_TTL: float = 300.0  # seconds


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
    global _ticker_set, _ticker_set_loaded_at
    import time
    if _ticker_set is None or (time.monotonic() - _ticker_set_loaded_at) > _TICKER_SET_TTL:
        _ticker_set = db.get_all_tickers()
        _ticker_set_loaded_at = time.monotonic()
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
    _wsj_defaults = [u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_WSJ_PODCAST]
    feed_1 = db.get_setting(1, "wsj_podcast_feed_1") or (_wsj_defaults[0] if len(_wsj_defaults) > 0 else "")
    feed_2 = db.get_setting(1, "wsj_podcast_feed_2") or (_wsj_defaults[1] if len(_wsj_defaults) > 1 else "")
    total = 0
    for url in filter(None, [feed_1, feed_2]):
        total += _process_podcast(url, NEWS_SOURCE_WSJ_PODCAST, max_episodes)
    return total


def fetch_morgan_stanley(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    url = db.get_setting(1, "morgan_stanley_feed") or next((u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MORGAN_STANLEY), "")
    return _process_podcast(url, NEWS_SOURCE_MORGAN_STANLEY, max_episodes)


def fetch_motley_fool(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    url = db.get_setting(1, "motley_fool_feed") or next((u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MOTLEY_FOOL), "")
    return _process_podcast(url, NEWS_SOURCE_MOTLEY_FOOL, max_episodes)


def fetch_all_podcasts(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    """
    Process every feed in PODCAST_FEEDS. Settings-table overrides apply to the
    legacy single-feed keys (wsj_podcast_feed_1/2, morgan_stanley_feed,
    motley_fool_feed) — all other feeds use the config URL directly.
    """
    # Build overrides from the settings table for the 4 legacy keys
    _wsj_defaults = [u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_WSJ_PODCAST]
    overrides: dict[str, str] = {}
    for setting_key, feed_url in [
        ("wsj_podcast_feed_1",  _wsj_defaults[0] if len(_wsj_defaults) > 0 else ""),
        ("wsj_podcast_feed_2",  _wsj_defaults[1] if len(_wsj_defaults) > 1 else ""),
        ("morgan_stanley_feed", next((u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MORGAN_STANLEY), "")),
        ("motley_fool_feed",    next((u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MOTLEY_FOOL), "")),
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
    api_key: str,
    source_name: str,
    query: str | None = None,
    source_ids: list[str] | None = None,
    max_articles: int = NEWSAPI_PAGE_SIZE,
) -> int:
    """Core NewsAPI fetch. Pass query, source_ids, or both. At least one is required."""
    if not query and not source_ids:
        return 0
    params: dict = {
        "apiKey":   api_key,
        "pageSize": min(max_articles, 100),
        "language": "en",
        "sortBy":   "publishedAt",
    }
    if query:
        params["q"] = query
    if source_ids:
        params["sources"] = ",".join(source_ids[:NEWSAPI_MAX_SOURCES_PER_CALL])

    try:
        resp = requests.get(NEWSAPI_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [{source_name}] NewsAPI request failed: {e}")
        return 0

    articles = data.get("articles") or []
    existing = db.get_news_article_urls(source_name)
    stored   = 0
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

    label = query or f"{len(source_ids or [])} sources"
    if stored:
        print(f"  [{source_name}] {stored} new articles ({label})")
    return stored


def refresh_newsapi_sources(user_uid: int = 1) -> int:
    """Fetch the full publisher list from /v2/sources and upsert to newsapi_sources table.
    Seeds default keywords on first call if the keywords table is empty.
    """
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [newsapi] No API key — set via Sources tab in scraper_app.")
        return 0
    try:
        resp = requests.get(
            NEWSAPI_SOURCES_URL,
            params={"apiKey": api_key, "language": "en"},
            timeout=15,
        )
        resp.raise_for_status()
        sources = resp.json().get("sources") or []
    except Exception as e:
        print(f"  [newsapi] Failed to fetch source list: {e}")
        return 0

    count = db.upsert_newsapi_sources(user_uid, sources)
    print(f"  [newsapi] {count} sources synced from NewsAPI.")

    if not db.get_newsapi_keywords(user_uid):
        for kw in NEWSAPI_DEFAULT_KEYWORDS:
            db.add_newsapi_keyword(user_uid, kw)
        print(f"  [newsapi] Seeded {len(NEWSAPI_DEFAULT_KEYWORDS)} default keywords.")

    return count


def fetch_newsapi_configured(user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Run NewsAPI fetch using all DB-configured sources and keywords.
    Sources are batched in groups of NEWSAPI_MAX_SOURCES_PER_CALL.
    Each enabled keyword is a separate query.
    """
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [newsapi] No API key.")
        return 0

    total = 0

    source_ids = [s["source_id"] for s in db.get_newsapi_sources(user_uid, enabled_only=True)]
    for i in range(0, len(source_ids), NEWSAPI_MAX_SOURCES_PER_CALL):
        batch = source_ids[i : i + NEWSAPI_MAX_SOURCES_PER_CALL]
        label = f"newsapi_sources"
        total += _fetch_newsapi_articles(api_key, label, source_ids=batch, max_articles=max_articles)
        time.sleep(NEWSAPI_RATE_LIMIT)

    for kw_row in db.get_newsapi_keywords(user_uid):
        if not kw_row["enabled"]:
            continue
        total += _fetch_newsapi_articles(
            api_key, NEWS_SOURCE_NEWSAPI,
            query=kw_row["keyword"],
            max_articles=max_articles,
        )
        time.sleep(NEWSAPI_RATE_LIMIT)

    print(f"  [newsapi] {total} total new articles from configured sources + keywords.")
    return total


def _get_nested(obj: dict, path: str):
    """Traverse a dot-notation path into a nested dict. Empty path returns obj."""
    if not path:
        return obj
    for key in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _get_api_key_row(name: str, user_uid: int) -> dict | None:
    """Return the api_keys row for this name, with plaintext key decoded."""
    row = db.query_one(
        "SELECT * FROM api_keys WHERE user_uid = ? AND name = ?", (user_uid, name)
    )
    if row is None:
        return None
    d = dict(row)
    try:
        import crypto as _crypto
        d["api_key_plain"] = _crypto.decrypt(d["api_key"]) if d.get("api_key") else None
    except Exception:
        d["api_key_plain"] = None
    return d


def test_news_connector(name: str, user_uid: int = 1) -> tuple[bool, str]:
    """Make one minimal request using the stored connector config.
    Returns (success, message) — message is shown in the TUI Logs tab.
    """
    row = _get_api_key_row(name, user_uid)
    if not row:
        return False, f"[{name}] No API key entry found."
    api_key = row.get("api_key_plain") or ""
    cfg = db.get_connector_config(user_uid, name)
    if not cfg:
        return False, f"[{name}] No connector config — configure the endpoint first."
    if not row.get("url"):
        return False, f"[{name}] No URL stored — set it in the connector config modal."

    params: dict = dict(cfg.get("extra_params") or {})
    page_param = cfg.get("page_size_param")
    if page_param:
        params[page_param] = 1
    kw_param = cfg.get("keyword_param")
    if kw_param:
        params[kw_param] = "news"

    headers: dict = {}
    auth_type  = cfg.get("auth_type", "query_param")
    auth_param = cfg.get("auth_param", "apiKey")
    match auth_type:
        case "query_param": params[auth_param] = api_key
        case "bearer":      headers["Authorization"] = f"Bearer {api_key}"
        case "header":      headers[auth_param] = api_key

    try:
        resp = requests.get(row["url"], params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = _get_nested(data, cfg.get("articles_path", "articles")) or []
        count = len(articles) if isinstance(articles, list) else "?"
        return True, f"[{name}] Connection OK — {count} article(s) in test response (HTTP {resp.status_code})"
    except Exception as exc:
        return False, f"[{name}] Connection FAILED: {exc}"


def fetch_generic_news_api(
    name: str,
    query: str | None = None,
    user_uid: int = 1,
    max_articles: int = NEWSAPI_PAGE_SIZE,
) -> int:
    """Fetch articles from any REST/JSON news API using its stored connector config.
    `name` is the api_keys.name (unique label). Returns number of new articles stored.
    """
    row = _get_api_key_row(name, user_uid)
    if not row:
        print(f"  [{name}] No API key entry found.")
        return 0
    api_key = row.get("api_key_plain") or ""
    cfg = db.get_connector_config(user_uid, name)
    if not cfg:
        print(f"  [{name}] No connector config — skipping.")
        return 0
    if not row.get("url"):
        print(f"  [{name}] No URL configured — skipping.")
        return 0

    source_label = row.get("display_name") or name
    page_size    = min(max_articles, cfg.get("default_page_size", 20))
    params: dict = dict(cfg.get("extra_params") or {})
    page_param   = cfg.get("page_size_param")
    if page_param:
        params[page_param] = page_size
    if query:
        kw_param = cfg.get("keyword_param")
        if kw_param:
            params[kw_param] = query

    headers: dict = {}
    auth_type  = cfg.get("auth_type", "query_param")
    auth_param = cfg.get("auth_param", "apiKey")
    match auth_type:
        case "query_param": params[auth_param] = api_key
        case "bearer":      headers["Authorization"] = f"Bearer {api_key}"
        case "header":      headers[auth_param] = api_key

    try:
        resp = requests.get(row["url"], params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  [{source_label}] Request failed: {exc}")
        return 0

    raw_articles = _get_nested(data, cfg.get("articles_path", "articles")) or []
    if not isinstance(raw_articles, list):
        print(f"  [{source_label}] Unexpected response shape — articles_path may be wrong.")
        return 0

    fm      = cfg.get("field_map", {})
    existing = db.get_news_article_urls(source_label)
    stored   = 0
    for art in raw_articles:
        url = str(art.get(fm.get("url", "url")) or "")
        if not url or url in existing:
            continue
        title   = str(art.get(fm.get("title", "title")) or "").strip()
        desc    = str(art.get(fm.get("description", "description")) or "")[:1000]
        body    = str(art.get(fm.get("body", "content")) or "")[:2000]
        pub_str = art.get(fm.get("published_at", "publishedAt"))
        if isinstance(pub_str, int):
            from datetime import datetime as _dt
            pub_str = _dt.utcfromtimestamp(pub_str).isoformat()

        tickers = _tag_tickers(f"{title} {desc} {body}")
        db.upsert_news_article({
            "source":       source_label,
            "headline":     title,
            "summary":      desc or None,
            "body":         body or None,
            "url":          url,
            "published_at": str(pub_str) if pub_str else None,
        })
        _store_ticker_signals(tickers, source_label, NEWS_SIGNAL_NEWS_HEADLINE,
                              f"Mentioned in '{title}'", url)
        time.sleep(NEWSAPI_RATE_LIMIT)
        stored += 1

    if stored:
        print(f"  [{source_label}] {stored} new articles")
    return stored


def fetch_all_generic_news_connectors(user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Run all enabled api_keys rows with role=news_connector.
    Each connector is run once per enabled keyword (shared keyword list), or once keyword-free
    if no keywords are configured.
    """
    connectors = db.get_api_keys_by_role(user_uid, ROLE_NEWS_CONNECTOR)
    enabled    = [c for c in connectors if c.get("connector_config") and c.get("url")]
    if not enabled:
        print("  [news_connectors] No configured connectors found.")
        return 0

    keywords = [k["keyword"] for k in db.get_newsapi_keywords(user_uid) if k["enabled"]]
    total    = 0
    for c in enabled:
        label = c.get("display_name") or c["name"]
        print(f"  [{label}]")
        if keywords:
            for kw in keywords:
                total += fetch_generic_news_api(c["name"], query=kw, user_uid=user_uid,
                                                max_articles=max_articles)
                time.sleep(NEWSAPI_RATE_LIMIT)
        else:
            total += fetch_generic_news_api(c["name"], user_uid=user_uid,
                                            max_articles=max_articles)
    print(f"  [news_connectors] {total} total new articles from {len(enabled)} connector(s).")
    return total


def fetch_newsapi(query: str, user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Fetch NewsAPI.org results for a one-off keyword query."""
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [newsapi] No API key — set via Sources tab in scraper_app.")
        return 0
    return _fetch_newsapi_articles(api_key, NEWS_SOURCE_NEWSAPI, query=query,
                                   max_articles=max_articles)


def fetch_reuters(user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Fetch Reuters via NewsAPI source filter (backwards-compat wrapper).
    Prefer enabling 'reuters' in the News tab for ongoing use.
    """
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [reuters] NewsAPI key required.")
        return 0
    return _fetch_newsapi_articles(api_key, NEWS_SOURCE_REUTERS,
                                   source_ids=["reuters"], max_articles=max_articles)


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


# ── LLM post-ingest classifier ────────────────────────────────────────────────

def classify_unclassified_articles(limit: int = 50) -> int:
    """
    Enqueue unclassified news_articles rows as 'classify_news' LLM jobs.

    Each article is marked classified immediately so it won't be re-enqueued.
    The llm.py --worker process picks up the jobs and handles supply_chain_events
    promotion when the GPU is free. This prevents parallel LLM execution (VRAM
    deadlock) and decouples ingest speed from model throughput.

    Returns count of jobs enqueued.
    """
    import json as _json

    articles = db.get_unclassified_news_articles(limit)
    if not articles:
        print("No unclassified news articles to process.")
        return 0

    enqueued = 0
    for article in articles:
        headline = article.get("headline") or ""
        body     = article.get("body") or article.get("summary") or ""
        db.mark_article_classified(article["article_uid"])
        if not headline:
            continue
        db.enqueue_llm_job(
            "classify_news",
            _json.dumps({"headline": headline, "body": body}),
            source_ref=f"article_uid:{article['article_uid']}",
        )
        enqueued += 1

    print(f"Enqueued {enqueued} classify_news jobs. Run 'python src/llm.py --worker' to process.")
    return enqueued


# ── Entry point ───────────────────────────────────────────────────────────────

def run(
    podcasts:         bool = False,
    yahoo_tickers:    list[str] | None = None,
    watchlist:        bool = False,
    wsj_pdf:          str | None = None,
    ingest_pdfs:      bool = False,
    ap:               bool = False,
    cnbc:             bool = False,
    marketwatch:      bool = False,
    reuters:          bool = False,
    newsapi_query:    str | None = None,
    newsapi_refresh:  bool = False,
    newsapi_all:      bool = False,
    connectors:       bool = False,
    gdelt_keywords:   list[str] | None = None,
    all_sources:      bool = False,
    classify:         bool = False,
    classify_limit:   int = 50,
    max_episodes:     int = NEWS_MAX_EPISODES,
    max_articles:     int = NEWS_MAX_ARTICLES,
    whisper_model:    str | None = None,
    user_uid:         int = 1,
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
        newsapi_all = True   # include configured NewsAPI sources + keywords when key is set
        connectors  = True   # include all news_connector role entries

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

    if newsapi_refresh:
        print("-- NewsAPI: Refresh source list -----------------")
        refresh_newsapi_sources(user_uid=user_uid)
        print()

    if newsapi_all:
        print("-- NewsAPI: All configured sources + keywords ---")
        n = fetch_newsapi_configured(user_uid=user_uid, max_articles=max_articles)
        print(f"   {n} new articles\n")
    if connectors:
        print("-- All News Connectors --------------------------")
        n = fetch_all_generic_news_connectors(user_uid=user_uid, max_articles=max_articles)
        print(f"   {n} new articles\n")

    elif newsapi_query:
        print(f"-- NewsAPI: '{newsapi_query}' -------------------")
        n = fetch_newsapi(newsapi_query, user_uid=user_uid, max_articles=max_articles)
        print(f"   {n} new articles\n")

    if gdelt_keywords:
        print(f"-- GDELT: {gdelt_keywords} ----------------------")
        n = fetch_gdelt(gdelt_keywords)
        print(f"   {n} new articles\n")

    if classify:
        print("-- LLM Disruption Classifier --------------------")
        classify_unclassified_articles(classify_limit)
        print()


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
    parser.add_argument("--reuters",         action="store_true", help="Fetch Reuters via NewsAPI source filter (backwards compat)")
    parser.add_argument("--newsapi",         metavar="QUERY",     help="One-off NewsAPI keyword query")
    parser.add_argument("--newsapi-refresh", action="store_true", help="Sync NewsAPI publisher list → newsapi_sources table; seed default keywords")
    parser.add_argument("--newsapi-all",     action="store_true", help="Run all DB-configured NewsAPI sources + keywords")
    parser.add_argument("--connectors",      action="store_true", help="Run all news_connector role entries (TheNewsAPI, Finnhub, etc.)")
    parser.add_argument("--gdelt",           nargs="+", metavar="KEYWORD", help="Fetch GDELT global event articles matching keywords")
    parser.add_argument("--all",             action="store_true", help="Run all sources (free RSS + configured NewsAPI sources + keywords)")
    parser.add_argument("--classify",     action="store_true",         help="Run LLM classifier on unclassified news_articles rows → supply_chain_events")
    parser.add_argument("--limit",        type=int, default=50, metavar="N", help="--classify only: max articles to classify per run (default 50)")
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
        newsapi_refresh=args.newsapi_refresh,
        newsapi_all=args.newsapi_all,
        connectors=args.connectors,
        gdelt_keywords=args.gdelt,
        all_sources=args.all,
        classify=args.classify,
        classify_limit=args.limit,
        max_episodes=args.episodes,
        max_articles=args.articles,
        whisper_model=args.model,
    )


if __name__ == "__main__":
    main()
