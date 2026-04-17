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
SCAN_TOP_N:         int   = 50
STALENESS_DAYS:     int   = 1     # refresh stock_financials if older than this

# ── Supply Chain Severity Rank ─────────────────────────────────────────────────
SEVERITY_RANK: dict[str, int] = {
    "CRITICAL": 4,
    "HIGH":     3,
    "MEDIUM":   2,
    "LOW":      1,
}
