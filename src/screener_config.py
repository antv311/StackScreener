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
DEBT_EQUITY_MAX:    float = 2.0
PEG_MAX:            float = 3.0

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

# ── Attribution ────────────────────────────────────────────────────────────────
DEFAULT_AUTHOR: str = "StackScreener"

# ── API Providers ──────────────────────────────────────────────────────────────
PROVIDER_FINVIZ:          str = "finviz"
PROVIDER_UNUSUAL_WHALES:  str = "unusual_whales"
PROVIDER_QUIVER_QUANT:    str = "quiver_quant"
PROVIDER_PLAID:           str = "plaid"
