import os

# ── Runtime ────────────────────────────────────────────────────────────────────
DEBUG_MODE: bool = False

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stackscreener.db")

# ── Scoring Weights ────────────────────────────────────────────────────────────
WEIGHT_EV_REVENUE:    float = 1.0
WEIGHT_PE:            float = 1.0
WEIGHT_EV_EBITDA:     float = 1.0
WEIGHT_PROFIT_MARGIN: float = 1.0
WEIGHT_PEG:           float = 1.0
WEIGHT_DEBT_EQUITY:   float = 1.0
WEIGHT_CFO_RATIO:     float = 1.0
WEIGHT_ALTMAN_Z:      float = 1.0
WEIGHT_SUPPLY_CHAIN:  float = 1.5  # additive bonus layer
WEIGHT_INST_FLOW:     float = 1.5  # additive bonus layer

# ── Scoring Thresholds ─────────────────────────────────────────────────────────
ALTMAN_Z_DISTRESS:  float = 1.81
ALTMAN_Z_SAFE:      float = 2.99

PE_MAX:             float = 50.0
EV_REVENUE_MAX:     float = 20.0
EV_EBITDA_MAX:      float = 30.0
DEBT_EQUITY_MAX:    float = 2.0
PEG_MAX:            float = 3.0
MARGIN_MIN:         float = -0.50   # net margin floor (score = 0)
MARGIN_MAX:         float =  0.30   # net margin ceiling (score = 100)

# ── Scan Modes ────────────────────────────────────────────────────────────────
SCAN_MODE_NSR:       str = "nsr"
SCAN_MODE_THEMATIC:  str = "thematic"
SCAN_MODE_WATCHLIST: str = "watchlist"
SCAN_MODE_CUSTOM:    str = "custom"

SCAN_MODES: frozenset[str] = frozenset({
    SCAN_MODE_NSR, SCAN_MODE_THEMATIC, SCAN_MODE_WATCHLIST, SCAN_MODE_CUSTOM,
})

# ── Scan Defaults ──────────────────────────────────────────────────────────────
SCAN_TOP_N:              int = 50
STALENESS_DAYS:          int = 1   # refresh fundamentals if older than this
HISTORY_STALENESS_DAYS:  int = 3   # accounts for weekends + holidays
IPO_LOOKAHEAD_DAYS:      int = 90

# ── Scan Status ────────────────────────────────────────────────────────────────
SCAN_STATUS_RUNNING:  str = "running"
SCAN_STATUS_COMPLETE: str = "complete"
SCAN_STATUS_FAILED:   str = "failed"

# ── Event Status ───────────────────────────────────────────────────────────────
EVENT_STATUS_ACTIVE:     str = "active"
EVENT_STATUS_RESOLVED:   str = "resolved"
EVENT_STATUS_MONITORING: str = "monitoring"

# ── Supply Chain Event Types ───────────────────────────────────────────────────
EVENT_TYPE_CONFLICT:         str = "conflict"
EVENT_TYPE_SANCTIONS:        str = "sanctions"
EVENT_TYPE_WEATHER:          str = "weather"
EVENT_TYPE_LABOR:            str = "labor"
EVENT_TYPE_ACCIDENT:         str = "accident"
EVENT_TYPE_PORT_BLOCKAGE:    str = "port_blockage"
EVENT_TYPE_FACTORY_SHUTDOWN: str = "factory_shutdown"
EVENT_TYPE_PANDEMIC:         str = "pandemic"

EVENT_TYPES: frozenset[str] = frozenset({
    EVENT_TYPE_CONFLICT,
    EVENT_TYPE_SANCTIONS,
    EVENT_TYPE_WEATHER,
    EVENT_TYPE_LABOR,
    EVENT_TYPE_ACCIDENT,
    EVENT_TYPE_PORT_BLOCKAGE,
    EVENT_TYPE_FACTORY_SHUTDOWN,
    EVENT_TYPE_PANDEMIC,
})

# ── Confidence Levels ──────────────────────────────────────────────────────────
CONFIDENCE_HIGH:   str = "high"
CONFIDENCE_MEDIUM: str = "medium"
CONFIDENCE_LOW:    str = "low"

# ── Supply Chain Event Severity ────────────────────────────────────────────────
SEVERITY_CRITICAL: str = "CRITICAL"
SEVERITY_HIGH:     str = "HIGH"
SEVERITY_MEDIUM:   str = "MEDIUM"
SEVERITY_LOW:      str = "LOW"

SEVERITY_RANK: dict[str, int] = {
    SEVERITY_CRITICAL: 4,
    SEVERITY_HIGH:     3,
    SEVERITY_MEDIUM:   2,
    SEVERITY_LOW:      1,
}

# ── Event Stock Roles ──────────────────────────────────────────────────────────
ROLE_IMPACTED:    str = "impacted"
ROLE_BENEFICIARY: str = "beneficiary"

# ── EDGAR ──────────────────────────────────────────────────────────────────────
EDGAR_RATE_LIMIT:        float = 0.11  # seconds between requests; SEC allows 10 req/s
EDGAR_STALENESS_DAYS:    int   = 90    # re-fetch XBRL facts quarterly
EDGAR_FILING_STALENESS:  int   = 180  # re-fetch 10-K text twice a year
# Identity string sent to SEC EDGAR in the User-Agent header (required by SEC fair-use policy)
EDGAR_IDENTITY:          str   = "StackScreener antv311@gmail.com"

FACT_GEOGRAPHIC_REVENUE:     str = "geographic_revenue"
FACT_CUSTOMER_CONCENTRATION: str = "customer_concentration"
FACT_RISK_FLAGS:             str = "risk_flags"        # boolean supply-chain risk indicators
FACT_FILING_CUSTOMERS:       str = "filing_customers"  # customer % mentions from 10-K text

# ── External Tools ────────────────────────────────────────────────────────────
# Absolute path to the directory containing ffmpeg.exe — prepended to PATH at
# runtime so Whisper can find it. Set to "" to rely on system PATH as-is.
FFMPEG_BIN_DIR: str = r"C:\tools\ffmpeg\bin"

# ── News Aggregation ───────────────────────────────────────────────────────────
NEWS_AUDIO_DIR:      str = "src/News/audio"   # temp MP3 storage — deleted after transcription
NEWS_PDF_DIR:        str = "src/News/pdfs"    # WSJ newspaper PDFs — kept
NEWS_WHISPER_MODEL:  str = "base"             # base | small | medium | large
NEWS_MAX_EPISODES:   int = 3                  # episodes per source per run
NEWS_TICKER_MIN_LEN: int = 2
NEWS_TICKER_MAX_LEN: int = 5

NEWS_SOURCE_WSJ_PODCAST:    str = "wsj_podcast"
NEWS_SOURCE_WSJ_PDF:        str = "wsj_pdf"
NEWS_SOURCE_MORGAN_STANLEY: str = "morgan_stanley_podcast"
NEWS_SOURCE_MOTLEY_FOOL:    str = "motley_fool_podcast"
NEWS_SOURCE_YAHOO_FINANCE:  str = "yahoo_finance_news"
NEWS_SOURCE_AP:             str = "ap_news"
NEWS_SOURCE_REUTERS:        str = "reuters_news"
NEWS_SOURCE_CNBC:           str = "cnbc_news"
NEWS_SOURCE_MARKETWATCH:    str = "marketwatch_news"
NEWS_SOURCE_NEWSAPI:        str = "newsapi"
NEWS_SOURCE_GDELT:          str = "gdelt"

NEWS_SIGNAL_TRANSCRIPT_MENTION: str = "transcript_mention"
NEWS_SIGNAL_NEWS_HEADLINE:      str = "news_headline"

NEWS_MAX_ARTICLES: int = 25   # max items per non-podcast source per run

# AP News RSS feeds (free, no key — verify URLs if feeds rotate)
AP_NEWS_RSS_FEEDS: list[tuple[str, str]] = [
    ("Business",   "https://feeds.ap.org/rss/apf-businessnews"),
    ("Finance",    "https://feeds.ap.org/rss/apf-finance"),
    ("Technology", "https://feeds.ap.org/rss/apf-technology"),
]

# CNBC RSS feeds (free, no key)
CNBC_RSS_FEEDS: list[tuple[str, str]] = [
    ("US Business", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("Finance",     "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
]

# MarketWatch RSS feed (free, no key)
MARKETWATCH_RSS_FEED: str = "https://feeds.marketwatch.com/marketwatch/topstories/"

# NewsAPI.org — free tier: 100 req/day. Reuters is fetched via domains="reuters.com".
NEWSAPI_BASE_URL:   str   = "https://newsapi.org/v2/everything"
NEWSAPI_PAGE_SIZE:  int   = 20
NEWSAPI_RATE_LIMIT: float = 1.0   # 1 s between requests (free tier: 100 req/day)

# GDELT Project — free, no key; global event database strong on physical disruptions
GDELT_BASE_URL:   str   = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_RATE_LIMIT: float = 0.5    # be polite to a free public API

# Default supply-chain keywords for GDELT and NewsAPI broad runs
SUPPLY_CHAIN_KEYWORDS: list[str] = [
    "supply chain disruption", "warehouse fire", "port closure",
    "factory shutdown", "logistics strike", "shipping delay",
]

PROVIDER_NEWSAPI: str = "newsapi"

# Podcast RSS feeds — URLs verified via iTunes API (April 2026).
# PODCAST_FEEDS is the canonical list used by fetch_all_podcasts().
# Each entry: (source_name, rss_url)
PODCAST_FEEDS: list[tuple[str, str]] = [
    (NEWS_SOURCE_WSJ_PODCAST,    "https://video-api.wsj.com/podcast/rss/wsj/minute-briefing"),
    (NEWS_SOURCE_WSJ_PODCAST,    "https://video-api.wsj.com/podcast/rss/wsj/tech-news-briefing"),
    (NEWS_SOURCE_WSJ_PODCAST,    "https://video-api.wsj.com/podcast/rss/wsj/whats-news"),
    (NEWS_SOURCE_WSJ_PODCAST,    "https://video-api.wsj.com/podcast/rss/wsj/your-money-matters"),
    (NEWS_SOURCE_MORGAN_STANLEY, "https://rss.art19.com/thoughts-on-the-market"),
    (NEWS_SOURCE_MOTLEY_FOOL,    "https://feeds.megaphone.fm/ARML8165884693"),   # Motley Fool Money
    (NEWS_SOURCE_MOTLEY_FOOL,    "https://feeds.megaphone.fm/ARML2428817190"),   # Rule Breaker Investing
]

# Legacy single-feed constants kept for backwards compat with the Settings panel.
WSJ_PODCAST_FEEDS: list[str] = [
    "https://video-api.wsj.com/podcast/rss/wsj/whats-news",
    "https://video-api.wsj.com/podcast/rss/wsj/minute-briefing",
]
MORGAN_STANLEY_PODCAST_FEED: str = "https://rss.art19.com/thoughts-on-the-market"
MOTLEY_FOOL_PODCAST_FEED:    str = "https://feeds.megaphone.fm/ARML8165884693"

# ── LLM Extraction Pipeline ───────────────────────────────────────────────────
# Test bed: Qwen2.5-7B-Instruct, TurboQuant 4-bit g=128 Hadamard (~4.4 GB VRAM)
# Production: Qwen2.5-32B-Instruct on P40 (~20 GB VRAM) — same constants
LLM_MODEL_ID:       str = "Qwen/Qwen2.5-7B-Instruct"
LLM_QUANTIZED_DIR:  str = "models/qwen2.5-7b-4bit"   # relative to repo root
LLM_BIT_WIDTH:      int = 4
LLM_GROUP_SIZE:     int = 128
LLM_MAX_NEW_TOKENS: int = 512

# ── Attribution ────────────────────────────────────────────────────────────────
DEFAULT_AUTHOR: str = "StackScreener"

# ── API Providers ──────────────────────────────────────────────────────────────
PROVIDER_FINVIZ:          str = "finviz"
PROVIDER_UNUSUAL_WHALES:  str = "unusual_whales"
PROVIDER_QUIVER_QUANT:    str = "quiver_quant"
PROVIDER_PLAID:           str = "plaid"
PROVIDER_GMAIL_WSJ:       str = "gmail_wsj"   # encrypted Gmail app password for WSJ fetcher
PROVIDER_SENATE_WATCHER:  str = "senate_watcher"
PROVIDER_HOUSE_WATCHER:   str = "house_watcher"

# ── Congressional Trades ───────────────────────────────────────────────────────
SENATE_WATCHER_URL:   str = "https://senatestockwatcher.com/api"
HOUSE_WATCHER_URL:    str = "https://housestockwatcher.com/api"
CONGRESS_LOOKBACK_DAYS: int = 180   # how far back to pull trades on first run
CONGRESS_BUY_SCORE:   float = 65.0  # sub_score for a congressional purchase signal
CONGRESS_SELL_SCORE:  float = 25.0  # sub_score for a congressional sale signal
SIGNAL_CONGRESS_BUY:  str = "congress_buy"
SIGNAL_CONGRESS_SELL: str = "congress_sell"

# ── WSJ PDF Fetcher ────────────────────────────────────────────────────────────
# Chrome profile that is already logged into WSJ — use login.py in WSJbot to refresh session.
WSJ_CHROME_PROFILE_DIR:  str = r"C:\Users\tony\WSJbot\chromeprofile"
WSJ_CHROME_PROFILE_NAME: str = "Default"

# Gmail filter — matches the daily delivery email from WSJ.
WSJ_EMAIL_FROM:    str = "access@interactive.wsj.com"
WSJ_EMAIL_SUBJECT: str = "Wall Street Journal Print Edition"

# Seconds to wait after navigating to the download URL before checking for the PDF.
WSJ_DOWNLOAD_WAIT_SECS: int = 20
# Max number of past days to backfill if the bookmark is stale.
WSJ_BACKFILL_LIMIT_DAYS: int = 50
# Settings key used to persist the last-successfully-downloaded edition date.
WSJ_LAST_POLLED_KEY: str = "wsj_last_polled"
# Settings key for the Gmail address (not sensitive — stored plaintext in settings).
WSJ_GMAIL_USER_KEY: str = "wsj_gmail_user"
