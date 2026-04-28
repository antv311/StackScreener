"""
tui/formatters.py — Pure formatting helpers shared across all TUI modules.
"""
from __future__ import annotations

from datetime import date, timedelta


def _fmt_mcap(v: float | None) -> str:
    if v is None:
        return "—"
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if v >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v:.0f}"


def _fmt_pct(v: float | None, decimals: int = 1) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v * 100:.{decimals}f}%"


def _fmt_pct_abs(v: float | None, decimals: int = 2) -> str:
    """Format as absolute percentage — no leading + sign. For yields, ratios, ownership."""
    if v is None:
        return "—"
    return f"{v * 100:.{decimals}f}%"


def _fmt_ratio(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{decimals}f}"


def _score_bar(score: float, width: int = 8) -> str:
    filled = round(score / 100 * width)
    return "█" * max(0, filled) + "░" * max(0, width - filled)


def _week_dates(week_offset: int = 0) -> list[date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    return [monday + timedelta(days=i) for i in range(7)]
