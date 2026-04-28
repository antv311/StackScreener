"""
news_utils.py — Shared utilities for the news pipeline submodules.

Imported by news_podcast.py, news_feeds.py, and news.py. Do not import
from those submodules here — this is the base of the import DAG.
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime

import db
from screener_config import (
    DEBUG_MODE,
    FFMPEG_BIN_DIR,
    NEWS_AUDIO_DIR,
    NEWS_PDF_DIR,
    NEWS_WHISPER_MODEL,
    NEWS_TICKER_MIN_LEN,
    NEWS_TICKER_MAX_LEN,
)

logger = logging.getLogger(__name__)

# Common English words and finance acronyms that look like tickers but aren't.
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
    if _ticker_set is None or (time.monotonic() - _ticker_set_loaded_at) > _TICKER_SET_TTL:
        _ticker_set = db.get_all_tickers()
        _ticker_set_loaded_at = time.monotonic()
    return _ticker_set


def _ensure_dirs() -> None:
    os.makedirs(NEWS_AUDIO_DIR, exist_ok=True)
    os.makedirs(NEWS_PDF_DIR, exist_ok=True)


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
