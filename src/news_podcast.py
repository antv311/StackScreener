"""
news_podcast.py — WSJ/Morgan Stanley/Motley Fool podcast pipeline + WSJ PDF ingest.

Fetches RSS feeds, downloads audio, transcribes with Whisper, and stores
articles + ticker signals. WSJ PDF ingest also lives here since it shares
the same tagging/storage pattern.
"""
from __future__ import annotations

import json
import logging
import os
import requests
from datetime import datetime
from xml.etree import ElementTree as ET

import db
from news_utils import (
    _ensure_dirs,
    _get_whisper_model,
    _tag_tickers,
    _store_ticker_signals,
)
from screener_config import (
    NEWS_AUDIO_DIR,
    NEWS_MAX_EPISODES,
    NEWS_PDF_DIR,
    NEWS_SIGNAL_TRANSCRIPT_MENTION,
    NEWS_SIGNAL_NEWS_HEADLINE,
    NEWS_SOURCE_WSJ_PODCAST,
    NEWS_SOURCE_WSJ_PDF,
    NEWS_SOURCE_MORGAN_STANLEY,
    NEWS_SOURCE_MOTLEY_FOOL,
    PODCAST_FEEDS,
)

logger = logging.getLogger(__name__)


# ── RSS + audio pipeline ──────────────────────────────────────────────────────

def _parse_rss(feed_url: str) -> list[dict]:
    """Fetch and parse a podcast RSS feed. Returns list of episode dicts."""
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
            data = json.loads(resp.text)
            # Podcast Index JSON transcript format
            if isinstance(data, dict) and "segments" in data:
                return " ".join(s.get("body", "") for s in data["segments"])
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


def _process_podcast(feed_url: str, source_name: str, max_episodes: int) -> int:
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
            if text:
                logger.debug("[%s] used embedded transcript: %s", source_name, ep["title"])

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
    url = db.get_setting(1, "morgan_stanley_feed") or next(
        (u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MORGAN_STANLEY), ""
    )
    return _process_podcast(url, NEWS_SOURCE_MORGAN_STANLEY, max_episodes)


def fetch_motley_fool(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    url = db.get_setting(1, "motley_fool_feed") or next(
        (u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MOTLEY_FOOL), ""
    )
    return _process_podcast(url, NEWS_SOURCE_MOTLEY_FOOL, max_episodes)


def fetch_all_podcasts(max_episodes: int = NEWS_MAX_EPISODES) -> int:
    """Process every feed in PODCAST_FEEDS. Settings-table overrides apply to the
    legacy single-feed keys (wsj_podcast_feed_1/2, morgan_stanley_feed, motley_fool_feed).
    """
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
            overrides[feed_url] = saved

    total = 0
    for source, url in PODCAST_FEEDS:
        effective_url = overrides.get(url, url)
        if not effective_url:
            continue
        total += _process_podcast(effective_url, source, max_episodes)
    return total


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
            logger.debug("  [%s] already ingested, skipping", fname)
            continue
        total += ingest_wsj_pdf(abs_path)

    return total
