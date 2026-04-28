"""
news_feeds.py — Article RSS, NewsAPI, generic connectors, and GDELT pipelines.

No audio/Whisper involved. All sources store articles and ticker signals.
"""
from __future__ import annotations

import logging
import re
import requests
import time
from datetime import datetime
from xml.etree import ElementTree as ET

import db
from news_utils import _tag_tickers, _store_ticker_signals
from screener_config import (
    AP_NEWS_RSS_FEEDS,
    CNBC_RSS_FEEDS,
    GDELT_BASE_URL,
    GDELT_RATE_LIMIT,
    MARKETWATCH_RSS_FEED,
    NEWS_MAX_ARTICLES,
    NEWS_SIGNAL_NEWS_HEADLINE,
    NEWS_SOURCE_AP,
    NEWS_SOURCE_CNBC,
    NEWS_SOURCE_GDELT,
    NEWS_SOURCE_LLOYDS_LIST,
    NEWS_SOURCE_MARKETWATCH,
    NEWS_SOURCE_NEWSAPI,
    NEWS_SOURCE_REUTERS,
    NEWS_SOURCE_RIO_TIMES,
    NEWSAPI_BASE_URL,
    NEWSAPI_DEFAULT_KEYWORDS,
    NEWSAPI_MAX_SOURCES_PER_CALL,
    NEWSAPI_PAGE_SIZE,
    NEWSAPI_RATE_LIMIT,
    NEWSAPI_SOURCES_URL,
    PROVIDER_LLOYDS_LIST,
    PROVIDER_NEWSAPI,
    RIO_TIMES_RSS_FEED,
    ROLE_NEWS_CONNECTOR,
)

logger = logging.getLogger(__name__)


# ── Article RSS pipeline ──────────────────────────────────────────────────────


def _ingest_rss_articles(
    feed_url: str,
    source_name: str,
    max_articles: int = NEWS_MAX_ARTICLES,
    auth: tuple[str, str] | None = None,
) -> int:
    """Fetch an article RSS feed, tag tickers, store deduplicated rows.

    auth: optional (username, password) tuple for HTTP Basic Auth.
    """
    try:
        resp = requests.get(
            feed_url, timeout=20,
            headers={"User-Agent": "StackScreener/1.0 (news aggregator)"},
            auth=auth,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items: list[dict] = []
        for item in root.findall(".//item")[:max_articles]:
            title = (item.findtext("title") or "").strip()
            link  = item.findtext("link") or ""
            desc  = (item.findtext("description") or "")[:1000]
            pub   = item.findtext("pubDate") or ""
            if title and link:
                items.append({"title": title, "url": link, "description": desc, "published": pub})
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


def fetch_rio_times(max_articles: int = NEWS_MAX_ARTICLES) -> int:
    """Fetch Rio Times Online RSS feed (free, no key — English Latin America/Brazil news)."""
    return _ingest_rss_articles(RIO_TIMES_RSS_FEED, NEWS_SOURCE_RIO_TIMES, max_articles)


def fetch_lloyds_list(user_uid: int = 1, max_articles: int = NEWS_MAX_ARTICLES) -> int:
    """Fetch Lloyd's List subscriber RSS feed.

    Lloyd's List provides personalized RSS URLs (with embedded auth token) to subscribers.
    Store the URL in the api_keys row for provider 'lloyds_list' via the Sources tab.

    HTTP Basic Auth is also supported: set connector_config = {"auth_type": "basic"} and
    store the subscriber username as the api_key value (password is derived from the key).
    """
    row = _get_api_key_row(PROVIDER_LLOYDS_LIST, user_uid)
    if not row or not row.get("url"):
        print(
            "  [lloyds_list] No subscriber RSS URL configured. "
            "Add a 'lloyds_list' entry in the Sources tab and paste your "
            "personalized RSS URL into the URL field."
        )
        return 0

    feed_url = row["url"]
    auth: tuple[str, str] | None = None

    cfg = db.get_connector_config(user_uid, PROVIDER_LLOYDS_LIST) or {}
    if cfg.get("auth_type") == "basic" and row.get("api_key_plain"):
        # api_key_plain stores the subscriber email; password may be stored
        # in connector_config["password"] or left empty for token-URL-only mode.
        username = row["api_key_plain"]
        password = cfg.get("password", "")
        auth = (username, password)

    total = 0
    # connector_config may supply additional section feed URLs to fetch alongside the primary
    extra_feeds: list[str] = cfg.get("extra_feeds") or []
    for url in [feed_url, *extra_feeds]:
        total += _ingest_rss_articles(url, NEWS_SOURCE_LLOYDS_LIST, max_articles, auth=auth)
    return total


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
    """Run NewsAPI fetch using all DB-configured sources and keywords."""
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [newsapi] No API key.")
        return 0

    total = 0
    source_ids = [s["source_id"] for s in db.get_newsapi_sources(user_uid, enabled_only=True)]
    for i in range(0, len(source_ids), NEWSAPI_MAX_SOURCES_PER_CALL):
        batch = source_ids[i : i + NEWSAPI_MAX_SOURCES_PER_CALL]
        total += _fetch_newsapi_articles(api_key, "newsapi_sources", source_ids=batch,
                                         max_articles=max_articles)
        time.sleep(NEWSAPI_RATE_LIMIT)

    for kw_row in db.get_newsapi_keywords(user_uid):
        if not kw_row["enabled"]:
            continue
        total += _fetch_newsapi_articles(api_key, NEWS_SOURCE_NEWSAPI,
                                         query=kw_row["keyword"], max_articles=max_articles)
        time.sleep(NEWSAPI_RATE_LIMIT)

    print(f"  [newsapi] {total} total new articles from configured sources + keywords.")
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
    """Fetch Reuters via NewsAPI source filter."""
    api_key = db.get_api_key(user_uid, PROVIDER_NEWSAPI)
    if not api_key:
        print("  [reuters] NewsAPI key required.")
        return 0
    return _fetch_newsapi_articles(api_key, NEWS_SOURCE_REUTERS,
                                   source_ids=["reuters"], max_articles=max_articles)


# ── Generic news connector pipeline ──────────────────────────────────────────

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
    """Fetch articles from any REST/JSON news API using its stored connector config."""
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

    fm       = cfg.get("field_map", {})
    existing = db.get_news_article_urls(source_label)
    stored   = 0
    for art in raw_articles:
        url   = _get_nested(art, fm.get("url", "url")) or ""
        if not url or url in existing:
            continue
        title = (_get_nested(art, fm.get("title", "title")) or "").strip()
        desc  = (_get_nested(art, fm.get("description", "description")) or "")[:1000]
        body  = (_get_nested(art, fm.get("body", "content")) or "")[:2000]
        pub_raw = _get_nested(art, fm.get("published_at", "publishedAt"))
        pub_str = str(pub_raw) if pub_raw else None

        tickers = _tag_tickers(f"{title} {desc} {body}")
        db.upsert_news_article({
            "source":       source_label,
            "headline":     title,
            "summary":      desc or None,
            "body":         body or None,
            "url":          url,
            "published_at": pub_str,
        })
        _store_ticker_signals(tickers, source_label, NEWS_SIGNAL_NEWS_HEADLINE,
                              f"Mentioned in '{title}'", url)
        time.sleep(NEWSAPI_RATE_LIMIT)
        stored += 1

    if stored:
        print(f"  [{source_label}] {stored} new articles")
    return stored


def fetch_all_generic_news_connectors(user_uid: int = 1, max_articles: int = NEWSAPI_PAGE_SIZE) -> int:
    """Run all enabled api_keys rows with role=news_connector."""
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
