"""
screener.py — Core scoring engine for StackScreener.

Scores each stock across 8 fundamental components plus optional
supply chain and institutional flow overlays. All outputs 0–100;
missing data returns a neutral 50 rather than failing the stock.

Component scores:
  score_ev_revenue    EV/Revenue     lower is better
  score_pe            Trailing P/E   lower is better
  score_ev_ebitda     EV/EBITDA      lower is better
  score_profit_margin Net margin     higher is better
  score_peg           PEG ratio      lower is better (0–1 is best)
  score_debt_equity   D/E ratio      lower is better
  score_cfo_ratio     CFO/Debt       placeholder — 50 until balance sheet data seeded
  score_altman_z      Altman Z       placeholder — 50 until balance sheet data seeded

Additive overlays (boost on top of fundamental base):
  score_supply_chain  Supply chain benefit signal
  score_inst_flow     Congressional/insider/institutional signal
"""

from screener_config import (
    WEIGHT_EV_REVENUE, WEIGHT_PE, WEIGHT_EV_EBITDA,
    WEIGHT_PROFIT_MARGIN, WEIGHT_PEG, WEIGHT_DEBT_EQUITY,
    WEIGHT_CFO_RATIO, WEIGHT_ALTMAN_Z,
    WEIGHT_SUPPLY_CHAIN, WEIGHT_INST_FLOW,
    PE_MAX, EV_REVENUE_MAX, EV_EBITDA_MAX,
    DEBT_EQUITY_MAX, PEG_MAX,
    MARGIN_MIN, MARGIN_MAX,
)

# Additive overlay cap: each overlay can add at most this many points to the base score.
_OVERLAY_MAX_BOOST: float = 20.0


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _score_pe(pe: float | None) -> float:
    if pe is None:
        return 50.0
    if pe <= 0:
        return 0.0
    return _clamp((PE_MAX - pe) / PE_MAX * 100.0)


def _score_ev_revenue(ev_r: float | None) -> float:
    if ev_r is None:
        return 50.0
    if ev_r <= 0:
        return 0.0
    return _clamp((EV_REVENUE_MAX - ev_r) / EV_REVENUE_MAX * 100.0)


def _score_ev_ebitda(ev_e: float | None) -> float:
    if ev_e is None:
        return 50.0
    if ev_e <= 0:
        return 0.0
    return _clamp((EV_EBITDA_MAX - ev_e) / EV_EBITDA_MAX * 100.0)


def _score_profit_margin(margin: float | None) -> float:
    if margin is None:
        return 50.0
    span = MARGIN_MAX - MARGIN_MIN
    return _clamp((margin - MARGIN_MIN) / span * 100.0)


def _score_peg(peg: float | None) -> float:
    if peg is None:
        return 50.0
    if peg <= 0:
        return 0.0
    if peg >= PEG_MAX:
        return 0.0
    return _clamp((PEG_MAX - peg) / PEG_MAX * 100.0)


def _score_debt_equity(de: float | None) -> float:
    if de is None:
        return 50.0
    if de < 0:
        return 0.0
    return _clamp((DEBT_EQUITY_MAX - de) / DEBT_EQUITY_MAX * 100.0)


def _weighted_composite(components: dict[str, float]) -> float:
    """Weighted average of 8 fundamental components + additive overlays."""
    weights: dict[str, float] = {
        "score_ev_revenue":    WEIGHT_EV_REVENUE,
        "score_pe":            WEIGHT_PE,
        "score_ev_ebitda":     WEIGHT_EV_EBITDA,
        "score_profit_margin": WEIGHT_PROFIT_MARGIN,
        "score_peg":           WEIGHT_PEG,
        "score_debt_equity":   WEIGHT_DEBT_EQUITY,
        "score_cfo_ratio":     WEIGHT_CFO_RATIO,
        "score_altman_z":      WEIGHT_ALTMAN_Z,
    }
    total_weight = sum(weights.values())
    base = sum(components[k] * w for k, w in weights.items()) / total_weight

    # Additive overlays: fractional boost scaled by WEIGHT_* / 1.5 (default weight)
    sc_boost = (components.get("score_supply_chain", 0.0) / 100.0
                * _OVERLAY_MAX_BOOST * (WEIGHT_SUPPLY_CHAIN / 1.5))
    if_boost = (components.get("score_inst_flow", 0.0) / 100.0
                * _OVERLAY_MAX_BOOST * (WEIGHT_INST_FLOW / 1.5))

    return _clamp(base + sc_boost + if_boost)


def score_stock(
    stock: dict,
    supply_chain_score: float = 0.0,
    inst_flow_score: float = 0.0,
) -> dict:
    """Score a single stock. Returns a dict of all component scores + composite_score.

    Args:
        stock: Row dict from the stocks table.
        supply_chain_score: 0–100 signal from supply chain event linkage.
        inst_flow_score: 0–100 signal from source_signals (congressional/insider/inst).

    Returns:
        dict with keys: composite_score, score_ev_revenue, score_pe, score_ev_ebitda,
        score_profit_margin, score_peg, score_debt_equity, score_cfo_ratio,
        score_altman_z, score_supply_chain, score_inst_flow.
    """
    components: dict[str, float] = {
        "score_ev_revenue":    _score_ev_revenue(stock.get("ev_revenue")),
        "score_pe":            _score_pe(stock.get("pe_ratio")),
        "score_ev_ebitda":     _score_ev_ebitda(stock.get("ev_ebitda")),
        "score_profit_margin": _score_profit_margin(stock.get("net_profit_margin")),
        "score_peg":           _score_peg(stock.get("peg_ratio")),
        "score_debt_equity":   _score_debt_equity(stock.get("total_debt_to_equity")),
        "score_cfo_ratio":     50.0,
        "score_altman_z":      50.0,
        "score_supply_chain":  _clamp(supply_chain_score),
        "score_inst_flow":     _clamp(inst_flow_score),
    }
    components["composite_score"] = _weighted_composite(components)
    return components
