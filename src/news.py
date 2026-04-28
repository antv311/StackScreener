"""
news.py — News and podcast aggregator orchestrator for StackScreener.

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
from __future__ import annotations

import argparse
import json as _json
import logging
from datetime import datetime

import yfinance as yf

import db
from news_utils import (
    _ensure_dirs,
    _get_ticker_set,
    _store_ticker_signals,
    set_whisper_model,
)
from news_podcast import (
    fetch_all_podcasts,
    fetch_morgan_stanley,
    fetch_motley_fool,
    fetch_wsj_podcasts,
    ingest_pending_pdfs,
    ingest_wsj_pdf,
)
from news_feeds import (
    fetch_ap_news,
    fetch_cnbc_news,
    fetch_gdelt,
    fetch_generic_news_api,
    fetch_all_generic_news_connectors,
    fetch_lloyds_list,
    fetch_marketwatch_news,
    fetch_newsapi,
    fetch_newsapi_configured,
    fetch_reuters,
    fetch_rio_times,
    refresh_newsapi_sources,
    test_news_connector,
)
from screener_config import (
    DEBUG_MODE,
    NEWS_MAX_ARTICLES,
    NEWS_MAX_EPISODES,
    NEWS_SIGNAL_NEWS_HEADLINE,
    NEWS_SOURCE_YAHOO_FINANCE,
)

logger = logging.getLogger(__name__)

# Re-export everything callers expect to find in news.*
__all__ = [
    # from news_podcast
    "fetch_all_podcasts", "fetch_morgan_stanley", "fetch_motley_fool",
    "fetch_wsj_podcasts", "ingest_pending_pdfs", "ingest_wsj_pdf",
    # from news_feeds
    "fetch_ap_news", "fetch_cnbc_news", "fetch_gdelt", "fetch_generic_news_api",
    "fetch_all_generic_news_connectors", "fetch_lloyds_list", "fetch_marketwatch_news",
    "fetch_newsapi", "fetch_newsapi_configured", "fetch_reuters", "fetch_rio_times",
    "refresh_newsapi_sources", "test_news_connector",
    # from news_utils
    "set_whisper_model",
    # local
    "fetch_yahoo_news", "fetch_watchlist_yahoo_news",
    "classify_unclassified_articles", "run", "main",
]


# ── Yahoo Finance pipeline ────────────────────────────────────────────────────

def fetch_yahoo_news(tickers: list[str]) -> int:
    """Fetch Yahoo Finance news for a list of tickers. No audio involved."""
    stored = 0
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

            logger.debug("  [%s] %s: %d items", NEWS_SOURCE_YAHOO_FINANCE, sym, len(items))
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
    rio_times:        bool = False,
    reuters:          bool = False,
    lloyds_list:      bool = False,
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
        rio_times   = True
        newsapi_all = True
        connectors  = True

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

    if rio_times:
        print("-- Rio Times Online RSS -------------------------")
        n = fetch_rio_times(max_articles)
        print(f"   {n} new articles\n")

    if lloyds_list:
        print("-- Lloyd's List RSS (subscriber) ----------------")
        n = fetch_lloyds_list(user_uid=user_uid, max_articles=max_articles)
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
    parser.add_argument("--ingest-pdfs",  action="store_true",         help=f"Ingest all new PDFs in src/News/pdfs/")
    parser.add_argument("--ap",           action="store_true",         help="Fetch AP News RSS (business + finance + technology)")
    parser.add_argument("--cnbc",         action="store_true",         help="Fetch CNBC RSS feeds")
    parser.add_argument("--marketwatch",  action="store_true",         help="Fetch MarketWatch RSS top stories")
    parser.add_argument("--rio-times",    action="store_true",         help="Fetch Rio Times Online RSS (free, Latin America/Brazil)")
    parser.add_argument("--lloyds-list",  action="store_true",         help="Fetch Lloyd's List subscriber RSS (configure URL in Sources tab)")
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
    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    run(
        podcasts=args.podcasts,
        yahoo_tickers=args.yahoo,
        watchlist=args.watchlist,
        wsj_pdf=args.wsj_pdf,
        ingest_pdfs=args.ingest_pdfs,
        ap=args.ap,
        cnbc=args.cnbc,
        marketwatch=args.marketwatch,
        rio_times=args.rio_times,
        reuters=args.reuters,
        lloyds_list=args.lloyds_list,
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
