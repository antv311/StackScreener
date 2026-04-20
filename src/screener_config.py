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
EDGAR_RATE_LIMIT:     float = 0.11  # seconds between requests; SEC allows 10 req/s
EDGAR_STALENESS_DAYS: int   = 90    # re-fetch XBRL facts quarterly

FACT_GEOGRAPHIC_REVENUE:     str = "geographic_revenue"
FACT_CUSTOMER_CONCENTRATION: str = "customer_concentration"

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

NEWS_SIGNAL_TRANSCRIPT_MENTION: str = "transcript_mention"
NEWS_SIGNAL_NEWS_HEADLINE:      str = "news_headline"

# Podcast RSS feeds — verify these against each show's current feed before first run.
# To find a feed: open the show in Apple Podcasts → share → copy RSS link.
WSJ_PODCAST_FEEDS: list[str] = [
    "https://feeds.simplecast.com/qm_9xx0g",  # The Journal (WSJ)
    "https://feeds.simplecast.com/7HRHEbex",  # What's News (WSJ)
]
MORGAN_STANLEY_PODCAST_FEED: str = "https://feeds.megaphone.fm/MSFS8299469162"  # Thoughts on the Market
MOTLEY_FOOL_PODCAST_FEED:    str = "https://feeds.megaphone.fm/foolmoneypodcast"  # Motley Fool Money

# ── Attribution ────────────────────────────────────────────────────────────────
DEFAULT_AUTHOR: str = "StackScreener"

# ── API Providers ──────────────────────────────────────────────────────────────
PROVIDER_FINVIZ:          str = "finviz"
PROVIDER_UNUSUAL_WHALES:  str = "unusual_whales"
PROVIDER_QUIVER_QUANT:    str = "quiver_quant"
PROVIDER_PLAID:           str = "plaid"
