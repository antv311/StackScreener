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
EVENT_TYPE_CONFLICT:           str = "conflict"
EVENT_TYPE_SANCTIONS:          str = "sanctions"
EVENT_TYPE_WEATHER:            str = "weather"
EVENT_TYPE_LABOR:              str = "labor"
EVENT_TYPE_ACCIDENT:           str = "accident"
EVENT_TYPE_PORT_BLOCKAGE:      str = "port_blockage"
EVENT_TYPE_FACTORY_SHUTDOWN:   str = "factory_shutdown"
EVENT_TYPE_PANDEMIC:           str = "pandemic"
EVENT_TYPE_FIRE:               str = "fire"
EVENT_TYPE_FLOOD:              str = "flood"
EVENT_TYPE_NATURAL_DISASTER:   str = "natural_disaster"
EVENT_TYPE_INFRASTRUCTURE:     str = "infrastructure_failure"
EVENT_TYPE_PRODUCT_RECALL:     str = "product_recall"
EVENT_TYPE_CYBER:              str = "cybersecurity"

EVENT_TYPES: frozenset[str] = frozenset({
    EVENT_TYPE_CONFLICT,
    EVENT_TYPE_SANCTIONS,
    EVENT_TYPE_WEATHER,
    EVENT_TYPE_LABOR,
    EVENT_TYPE_ACCIDENT,
    EVENT_TYPE_PORT_BLOCKAGE,
    EVENT_TYPE_FACTORY_SHUTDOWN,
    EVENT_TYPE_PANDEMIC,
    EVENT_TYPE_FIRE,
    EVENT_TYPE_FLOOD,
    EVENT_TYPE_NATURAL_DISASTER,
    EVENT_TYPE_INFRASTRUCTURE,
    EVENT_TYPE_PRODUCT_RECALL,
    EVENT_TYPE_CYBER,
})

# ── Confidence Levels ──────────────────────────────────────────────────────────
CONFIDENCE_HIGH:   str = "high"
CONFIDENCE_MEDIUM: str = "medium"
CONFIDENCE_LOW:    str = "low"

# Score multiplier applied to supply-chain beneficiary scores by confidence tier.
SC_CONFIDENCE_MULT: dict[str, float] = {
    "high":   1.0,
    "medium": 0.75,
    "low":    0.50,
}

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
# User-Agent strings for commodity and logistics HTTP requests
COMMODITIES_USER_AGENT:  str   = "StackScreener/1.0 commodities@stackscreener.local"
LOGISTICS_USER_AGENT:    str   = "StackScreener/1.0 logistics@stackscreener.local"
FILINGS_CACHE_DIR:       str   = "src/filings"  # 10-K → src/filings/10k/  8-K → src/filings/8k/

FACT_GEOGRAPHIC_REVENUE:     str = "geographic_revenue"
FACT_CUSTOMER_CONCENTRATION: str = "customer_concentration"
FACT_RISK_FLAGS:             str = "risk_flags"        # boolean supply-chain risk indicators
FACT_FILING_CUSTOMERS:       str = "filing_customers"  # customer % mentions from 10-K text
FACT_8K_EVENTS:              str = "8k_material_events" # keyword-flagged 8-K material events
FACT_LLM_10K_ENTITIES:       str = "llm_10k_entities"  # LLM-extracted supplier/customer entities

EDGAR_8K_LOOKBACK_DAYS:  int   = 30   # fetch 8-Ks filed in last 30 days
EDGAR_8K_STALENESS_DAYS: int   = 7    # re-check 8-Ks weekly

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

# NewsAPI.org — free tier: 100 req/day.
NEWSAPI_BASE_URL:             str        = "https://newsapi.org/v2/everything"
NEWSAPI_SOURCES_URL:          str        = "https://newsapi.org/v2/sources"
NEWSAPI_TOP_HEADLINES_URL:    str        = "https://newsapi.org/v2/top-headlines"
NEWSAPI_PAGE_SIZE:            int        = 20
NEWSAPI_RATE_LIMIT:           float      = 1.0    # 1 s between requests (free tier: 100 req/day)
NEWSAPI_MAX_SOURCES_PER_CALL: int        = 20     # API hard limit per request
# ── Generic news connector templates ─────────────────────────────────────────
# Each template describes how to call a REST/JSON news API.
# Stored as connector_config JSON on api_keys rows.
# Fields:
#   auth_type    : "query_param" | "bearer" | "header"
#   auth_param   : param name (query_param) or header name (header)
#   articles_path: top-level key in the JSON response that holds the articles array
#   keyword_param: query parameter name for keyword search
#   page_size_param: query parameter name for page/limit size
#   default_page_size: default number of articles per request
#   field_map    : maps our internal field names → vendor field names
#   extra_params : fixed params always included in every request
CONNECTOR_TEMPLATES: dict[str, dict] = {
    "NewsAPI.org": {
        "auth_type":         "query_param",
        "auth_param":        "apiKey",
        "articles_path":     "articles",
        "keyword_param":     "q",
        "page_size_param":   "pageSize",
        "default_page_size": 20,
        "field_map": {
            "title":        "title",
            "url":          "url",
            "description":  "description",
            "body":         "content",
            "published_at": "publishedAt",
        },
        "extra_params": {"language": "en", "sortBy": "publishedAt"},
    },
    "TheNewsAPI": {
        "auth_type":         "query_param",
        "auth_param":        "api_token",
        "articles_path":     "data",
        "keyword_param":     "search",
        "page_size_param":   "limit",
        "default_page_size": 25,
        "field_map": {
            "title":        "title",
            "url":          "url",
            "description":  "description",
            "body":         "snippet",
            "published_at": "published_at",
        },
        "extra_params": {"language": "en"},
    },
    "Finnhub": {
        "auth_type":         "header",
        "auth_param":        "X-Finnhub-Token",
        "articles_path":     "",
        "keyword_param":     "q",
        "page_size_param":   "",
        "default_page_size": 50,
        "field_map": {
            "title":        "headline",
            "url":          "url",
            "description":  "summary",
            "body":         "summary",
            "published_at": "datetime",
        },
        "extra_params": {},
    },
    "Alpha Vantage": {
        "auth_type":         "query_param",
        "auth_param":        "apikey",
        "articles_path":     "feed",
        "keyword_param":     "tickers",
        "page_size_param":   "limit",
        "default_page_size": 50,
        "field_map": {
            "title":        "title",
            "url":          "url",
            "description":  "summary",
            "body":         "summary",
            "published_at": "time_published",
        },
        "extra_params": {"sort": "LATEST"},
    },
    "Generic (customize)": {
        "auth_type":         "query_param",
        "auth_param":        "apiKey",
        "articles_path":     "articles",
        "keyword_param":     "q",
        "page_size_param":   "pageSize",
        "default_page_size": 20,
        "field_map": {
            "title":        "title",
            "url":          "url",
            "description":  "description",
            "body":         "content",
            "published_at": "publishedAt",
        },
        "extra_params": {},
    },
}

NEWSAPI_DEFAULT_KEYWORDS: list[str] = [
    "supply chain disruption",
    "warehouse fire",
    "port closure",
    "factory shutdown",
    "product recall",
    "shipping delay",
    "trade sanctions",
    "commodity shortage",
]

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
SIGNAL_CONGRESS_BUY:   str = "congress_buy"
SIGNAL_CONGRESS_SELL:  str = "congress_sell"
SIGNAL_INSIDER_BUY:    str = "insider_buy"
SIGNAL_INSIDER_SELL:   str = "insider_sell"
SIGNAL_MATERIAL_EVENT: str = "material_event"

INSIDER_BUY_SCORE:     float = 70.0  # sub_score for insider purchase signal
INSIDER_SELL_SCORE:    float = 20.0  # sub_score for insider sale signal
MATERIAL_EVENT_SCORE:  float = 55.0  # sub_score for 8-K material event signal

FORM4_LOOKBACK_DAYS: int = 90  # default Form 4 lookback window

PROVIDER_SEC_EDGAR: str = "sec_edgar"  # provider name for Form 4 + 8-K source_signals

LLM_CLASSIFY_CONFIDENCE_THRESHOLD: float = 0.7  # min confidence to auto-promote to supply_chain_events

# ── Options Flow ───────────────────────────────────────────────────────────────
SIGNAL_OPTIONS_UNUSUAL: str = "unusual_options"
OPTIONS_CALL_SCORE:     float = 65.0   # bullish unusual call volume signal
OPTIONS_PUT_SCORE:      float = 30.0   # bearish unusual put volume signal
OPTIONS_VOLUME_MULT:    float = 3.0    # flag if volume > N × open_interest (proxy for baseline)
OPTIONS_MIN_VOLUME:     int   = 500    # ignore tiny contracts (noise filter)
OPTIONS_LOOKBACK_DAYS:  int   = 90     # how far back to look for stale signals
PROVIDER_OPTIONS:       str   = "yfinance_options"

# ── Form 13F Institutional Holdings ───────────────────────────────────────────
SIGNAL_INST_BUY:        str   = "inst_buy"
SIGNAL_INST_SELL:       str   = "inst_sell"
INST_BUY_SCORE:         float = 60.0   # sub_score for institutional position increase
INST_SELL_SCORE:        float = 30.0   # sub_score for institutional position decrease
FORM13F_LOOKBACK_DAYS:  int   = 120    # re-fetch when quarterly filing is stale
PROVIDER_13F:           str   = "sec_13f"

# Top institutional investment managers by AUM — CIK zero-padded to 10 digits.
# Source: SEC EDGAR EDGAR filer lookup. Expand as needed.
INSTITUTION_CIKS: list[tuple[str, str]] = [
    ("0001067983", "Berkshire Hathaway"),
    ("0001364742", "BlackRock"),
    ("0000102909", "Vanguard Group"),
    ("0000093751", "State Street"),
    ("0000080255", "T. Rowe Price"),
    ("0000315066", "Fidelity (FMR)"),
    ("0000914208", "Invesco"),
    ("0000886982", "Goldman Sachs Asset Mgmt"),
    ("0000895421", "JP Morgan Asset Mgmt"),
    ("0001166559", "Citadel Advisors"),
    ("0001423053", "Renaissance Technologies"),
    ("0001037389", "D.E. Shaw"),
    ("0001336528", "AQR Capital Mgmt"),
    ("0001113838", "Two Sigma Investments"),
]

# ── Home Heatmap ───────────────────────────────────────────────────────────────
HEATMAP_DEFAULT_LIMIT:       int   = 200    # default tile count (all-stocks filter)
HEATMAP_LARGE_CAP_THRESHOLD: float = 10e9   # $10B — Large Cap filter
HEATMAP_MEGA_CAP_THRESHOLD:  float = 200e9  # $200B — Mega Cap filter
HEATMAP_SP500_LIMIT:         int   = 500    # approx S&P 500 by top 500 market cap

# ── USDA Crop Conditions (upstream commodity signals) ─────────────────────────
USDA_API_BASE:             str   = "https://quickstats.nass.usda.gov/api/api_GET/"
USDA_API_KEY_NAME:         str   = "usda_nass"          # key stored in api_keys table
SIGNAL_CROP_STRESS:        str   = "crop_stress"
CROP_STRESS_SCORE:         float = 45.0
CROP_GOOD_EXCELLENT_THRESHOLD: float = 0.05  # 5pp below 5-yr avg → signal
PROVIDER_USDA:             str   = "usda_nass"

# ── EIA Petroleum Inventory (upstream commodity signals) ──────────────────────
EIA_API_BASE:              str   = "https://api.eia.gov/v2"
EIA_API_KEY_NAME:          str   = "eia"                # key stored in api_keys table
SIGNAL_OIL_INVENTORY:      str   = "oil_inventory_surprise"
OIL_SURPRISE_SCORE:        float = 50.0
OIL_SURPRISE_THRESHOLD:    float = 0.05  # ±5% vs 5-week rolling avg → signal
PROVIDER_EIA:              str   = "eia"

# ── FRED Commodity Prices (upstream commodity signals) ────────────────────────
# Combination of World Bank spot prices + BLS PPI series hosted on FRED.
# Free key at https://fredaccount.stlouisfed.org → API Keys tab.
FRED_API_BASE:              str   = "https://api.stlouisfed.org/fred"
FRED_API_KEY_NAME:          str   = "fred"              # key stored in api_keys table
PROVIDER_FRED:              str   = "fred"

# Signal types per commodity category
SIGNAL_FERTILIZER_SURGE:    str   = "fertilizer_price_surge"
SIGNAL_NATGAS_SURGE:        str   = "natgas_price_surge"
SIGNAL_METAL_SURGE:         str   = "metal_price_surge"
SIGNAL_AGRICULTURAL_SURGE:  str   = "agricultural_price_surge"
SIGNAL_LUMBER_SURGE:        str   = "lumber_price_surge"

# Surge scores and thresholds per category
FERTILIZER_SURGE_SCORE:     float = 60.0
FERTILIZER_SURGE_THRESHOLD: float = 0.15  # fertilizers less volatile — 15% bar
NATGAS_SURGE_SCORE:         float = 65.0
NATGAS_SURGE_THRESHOLD:     float = 0.25  # nat gas highly volatile — 25% bar
METAL_SURGE_SCORE:          float = 55.0
METAL_SURGE_THRESHOLD:      float = 0.20  # LME metals — 20% bar
AGRICULTURAL_SURGE_SCORE:   float = 50.0
AGRICULTURAL_SURGE_THRESHOLD: float = 0.15
LUMBER_SURGE_SCORE:         float = 50.0
LUMBER_SURGE_THRESHOLD:     float = 0.20

# ── AIS Chokepoint Monitoring (midstream vessel signals) ──────────────────────
AIS_API_BASE:              str   = "wss://stream.aisstream.io/v0/stream"
AIS_API_KEY_NAME:          str   = "aisstream"          # key stored in api_keys table
AIS_SAMPLE_SECONDS:        int   = 60                   # websocket sample window
CHOKEPOINT_BASELINE_DAYS:  int   = 30
CHOKEPOINT_LOW_THRESHOLD:  float = 0.6    # < 60% of baseline → HIGH severity
SIGNAL_CHOKEPOINT:         str   = "chokepoint_congestion"
CHOKEPOINT_SCORE:          float = 60.0
PROVIDER_AIS:              str   = "aisstream"

# ── Panama Canal Draft Restrictions ───────────────────────────────────────────
PANAMA_STATS_URL:          str   = "https://www.pancanal.com/eng/op/aqRestricciones.html"
PANAMA_API_KEY_NAME:       str   = "panama_canal"       # unused — public endpoint
SIGNAL_CANAL_DRAFT:        str   = "canal_draft_restriction"
CANAL_DRAFT_SCORE:         float = 55.0
CANAL_DRAFT_LOW_THRESHOLD: float = 12.0   # max draft (metres) below this → HIGH
CANAL_NORMAL_DRAFT:        float = 13.4   # historical normal max draft (metres)
PROVIDER_PANAMA:           str   = "panama_canal"

# ── Known API roles ───────────────────────────────────────────────────────────
# Canonical list of (role_key, description) pairs used by the Sources tab dropdown.
# role_key must exactly match the value each module passes to db.get_api_key().
# Add new entries here when wiring in a new paid/key-gated data source.
ROLE_NEWS_CONNECTOR: str = "news_connector"  # role shared by all generic news API entries

KNOWN_API_ROLES: list[tuple[str, str]] = [
    (PROVIDER_NEWSAPI,    "NewsAPI.org — AP, Reuters, 150k+ sources (1-day delay on free)"),
    (AIS_API_KEY_NAME,    "AISstream — vessel tracking at chokepoints"),
    (USDA_API_KEY_NAME,   "USDA NASS — crop condition reports"),
    (EIA_API_KEY_NAME,    "EIA — weekly petroleum inventory"),
    (FRED_API_KEY_NAME,   "FRED — fertilizer prices (Urea, DAP, Potash), free key"),
    (PROVIDER_GMAIL_WSJ,  "Gmail app password — WSJ PDF delivery"),
    (ROLE_NEWS_CONNECTOR, "News Connector — generic REST/JSON news API (add as many as you want)"),
]

# ── Chokepoint definitions ────────────────────────────────────────────────────
# Each entry: lat/lon centre + bounding box for AIS vessel counting.
# Also used by the TUI world-map to place markers.
CHOKEPOINTS: dict[str, dict] = {
    "Strait of Hormuz":    {"lat": 26.6,  "lon":  56.3, "lat_min": 26.0, "lat_max": 27.5, "lon_min": 55.5, "lon_max": 57.5},
    "Strait of Malacca":   {"lat":  2.5,  "lon": 102.0, "lat_min":  1.0, "lat_max":  6.0, "lon_min": 99.0, "lon_max": 104.5},
    "Suez Canal":          {"lat": 30.5,  "lon":  32.3, "lat_min": 29.0, "lat_max": 32.5, "lon_min": 31.5, "lon_max": 33.0},
    "Bab el-Mandeb":       {"lat": 12.5,  "lon":  43.4, "lat_min": 11.5, "lat_max": 13.0, "lon_min": 42.5, "lon_max": 44.0},
    "Taiwan Strait":       {"lat": 24.0,  "lon": 120.5, "lat_min": 22.0, "lat_max": 26.0, "lon_min": 119.5, "lon_max": 122.0},
    "English Channel":     {"lat": 51.0,  "lon":   1.0, "lat_min": 50.0, "lat_max": 52.0, "lon_min":  -2.0, "lon_max":   3.0},
    "Strait of Gibraltar": {"lat": 36.0,  "lon":  -5.5, "lat_min": 35.5, "lat_max": 36.5, "lon_min":  -6.0, "lon_max":  -5.0},
    "Turkish Straits":     {"lat": 41.0,  "lon":  29.0, "lat_min": 40.5, "lat_max": 41.5, "lon_min":  28.5, "lon_max":  30.0},
    "Panama Canal":        {"lat":  9.1,  "lon": -79.7, "lat_min":  8.5, "lat_max": 10.0, "lon_min": -80.5, "lon_max": -79.0},
    "Danish Straits":      {"lat": 57.5,  "lon":  10.5, "lat_min": 55.5, "lat_max": 58.5, "lon_min":   9.5, "lon_max":  12.5},
}

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

# ── TUI Display Config ────────────────────────────────────────────────────────
# These constants drive the Bloomberg TUI (app.py) display logic.
# Kept here so they can be tuned without touching UI code.

# Screener tab — market-cap bucket boundaries (lower bound, $ float).
SCREENER_MCAP_BUCKETS: dict[str, float] = {
    "Mega (>200B)": 200e9,
    "Large (10B+)": 10e9,
    "Mid (2B+)":    2e9,
    "Small (<2B)":  0.0,
}

# Screener tab — P/E score range buckets (display label → (min, max) score).
SCREENER_PE_BUCKETS: dict[str, tuple[int, int]] = {
    "<15":    (0,    15),
    "15–25":  (15,   25),
    "25–50":  (25,   50),
    ">50":    (50, 9999),
}

# Calendar tab — event type → Rich color for DayCell rendering.
CALENDAR_EVENT_STYLES: dict[str, str] = {
    "earnings":     "green",
    "split":        "cyan",
    "ipo":          "yellow",
    "economic":     "magenta",
    "ex_dividend":  "gold1",
    "dividend_pay": "orange3",
}

# Stock Picks tab — source key → human-readable label.
SIGNAL_SOURCE_LABELS: dict[str, str] = {
    "senate_watcher": "Senate Watcher",
    "house_watcher":  "House Watcher",
    "sec_form4":      "SEC Form 4",
    "sec_13f":        "SEC 13F",
    "yahoo_finance":  "Yahoo Finance",
    "options_flow":   "Options Flow",
}

# Home heatmap — (pct_change_threshold, background_color) pairs, highest first.
HEATMAP_COLORS: list[tuple[float, str]] = [
    ( 3.0, "#0d5c0d"),
    ( 1.5, "#165e16"),
    ( 0.3, "#1e4d1e"),
    ( 0.0, "#2a2a2a"),
    (-1.5, "#4d1e1e"),
    (-3.0, "#5e1616"),
    (-9e9, "#6b0d0d"),
]

# Home heatmap — filter button (label, widget_id) pairs.
HEATMAP_FILTERS: list[tuple[str, str]] = [
    ("All",       "hf-all"),
    ("Large Cap", "hf-largecap"),
    ("Mega Cap",  "hf-megacap"),
    ("S&P ≈500",  "hf-sp500"),
    ("Watchlist", "hf-watchlist"),
]
