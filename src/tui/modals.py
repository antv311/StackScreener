"""
tui/modals.py — StockQuoteModal: full-screen quote overlay.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static, TabbedContent, TabPane

import db
from screener_config import FILINGS_CACHE_DIR
from .formatters import _fmt_mcap, _fmt_pct, _fmt_pct_abs, _fmt_ratio


class StockQuoteModal(ModalScreen[None]):
    """Full-screen quote overlay: fundamentals, signals, price history, news."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q",      "dismiss", "Close"),
    ]
    CSS = """
    StockQuoteModal { align: center middle; }
    #quote-box {
        width: 96%;
        height: 92%;
        background: $surface;
        border: solid $primary;
    }
    #quote-header {
        height: 3;
        padding: 0 2;
        background: $surface-darken-1;
        border-bottom: solid $border;
        content-align: left middle;
    }
    #quote-tabs { height: 1fr; }
    TabPane { height: 1fr; padding: 1 2; }
    #qt-overview  { height: 1fr; overflow-y: auto; }
    #qt-signals   { height: 1fr; }
    #qt-history   { height: 1fr; }
    #qt-news      { height: 1fr; overflow-y: auto; }
    #qt-filings   { height: 1fr; layout: vertical; }
    #qt-filings-table { height: 8; }
    #qt-filing-text { height: 1fr; overflow-y: auto; }
    """

    def __init__(self, ticker: str) -> None:
        self._ticker = ticker.upper()
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="quote-box"):
            yield Static("", id="quote-header")
            with TabbedContent(id="quote-tabs"):
                with TabPane("Overview"):
                    yield ScrollableContainer(
                        Static("", id="qt-overview-content"), id="qt-overview"
                    )
                with TabPane("Signals"):
                    yield DataTable(id="qt-signals", cursor_type="row")
                with TabPane("History"):
                    yield DataTable(id="qt-history", cursor_type="row")
                with TabPane("News"):
                    yield ScrollableContainer(
                        Static("", id="qt-news-content"), id="qt-news"
                    )
                with TabPane("Filings"):
                    with Vertical(id="qt-filings"):
                        yield DataTable(id="qt-filings-table", cursor_type="row")
                        yield ScrollableContainer(
                            Static("", id="qt-filing-text-content"), id="qt-filing-text"
                        )

    def on_mount(self) -> None:
        self._load()

    def _load(self) -> None:
        stock = db.get_stock_by_ticker(self._ticker)
        if not stock:
            self.query_one("#quote-header", Static).update(
                f"[red]  {self._ticker} — not found in database[/red]  [dim][ESC] close[/dim]"
            )
            return
        self._render_header(stock)
        self._render_overview(stock)
        self._render_signals(stock)
        self._render_history(stock)
        self._render_news(stock)
        self._render_filings(stock)

    def _render_header(self, s: dict) -> None:
        price     = s.get("price") or 0.0
        chg       = s.get("change_pct")
        chg_val   = chg / 100 if chg is not None else None
        chg_str   = _fmt_pct(chg_val)
        chg_style = "green" if (chg or 0) >= 0 else "red"
        name      = s.get("company_name") or self._ticker

        text = Text()
        text.append(f" {self._ticker} ", style="bold black on bright_white")
        text.append(f"  {name[:40]}  ", style="bold")
        text.append(f"${price:.2f}  ", style="bold green")
        text.append(chg_str, style=chg_style)
        text.append(f"  {_fmt_mcap(s.get('market_cap'))}  ", style="dim")
        text.append(f"{s.get('sector') or '—'}  ", style="dim")
        text.append(f"{s.get('exchange') or '—'}  ", style="dim")
        text.append("  [ESC/Q] close", style="dim italic")
        self.query_one("#quote-header", Static).update(text)

    def _render_overview(self, s: dict) -> None:
        def p(v: float | None) -> str:
            return _fmt_pct(v) if v is not None else "—"

        def r(v: float | None, d: int = 2) -> str:
            return _fmt_ratio(v, d) if v is not None else "—"

        a = _fmt_pct_abs

        sections: list[tuple[str, list[tuple[str, str]]]] = [
            ("VALUATION", [
                ("P/E (TTM)",           r(s.get("pe_ratio"), 1)),
                ("Forward P/E",         r(s.get("forward_pe"), 1)),
                ("PEG Ratio",           r(s.get("peg_ratio"))),
                ("P/S Ratio",           r(s.get("ps_ratio"))),
                ("P/B Ratio",           r(s.get("pb_ratio"))),
                ("Market Cap",          _fmt_mcap(s.get("market_cap"))),
            ]),
            ("DIVIDENDS", [
                ("Dividend Yield",      a(s.get("dividend_yield"))),
                ("Payout Ratio",        a(s.get("payout_ratio"))),
                ("Last Dividend",       f"${s['last_dividend_value']:.4f}" if s.get("last_dividend_value") else "—"),
                ("Ex-Dividend Date",    (s.get("ex_dividend_date") or "—")[:10]),
                ("Pay Date",            (s.get("dividend_date") or "—")[:10]),
            ]),
            ("MARGINS & RETURNS", [
                ("Gross Margin",        p(s.get("gross_margin"))),
                ("Operating Margin",    p(s.get("operating_margin"))),
                ("Net Margin",          p(s.get("net_profit_margin"))),
                ("Return on Assets",    p(s.get("return_on_assets"))),
                ("Return on Equity",    p(s.get("return_on_equity"))),
                ("Return on Invest.",   p(s.get("return_on_investment"))),
            ]),
            ("GROWTH", [
                ("EPS Growth (TTM)",    p(s.get("eps_growth_this_year"))),
                ("EPS Growth (Next Y)", p(s.get("eps_growth_next_year"))),
                ("EPS Growth (5Y est)", p(s.get("eps_growth_next_5_years"))),
                ("EPS Growth (5Y act)", p(s.get("eps_growth_past_5_years"))),
                ("Sales Growth (5Y)",   p(s.get("sales_growth_past_5_years"))),
                ("Sales Growth (QoQ)",  p(s.get("sales_growth_qoq"))),
                ("EPS Growth (QoQ)",    p(s.get("eps_growth_qoq"))),
            ]),
            ("RISK & TECHNICALS", [
                ("Beta",                r(s.get("beta"))),
                ("RSI (14)",            r(s.get("rsi_14"), 1)),
                ("ATR",                 r(s.get("atr"))),
                ("Debt/Equity (LT)",    r(s.get("lt_debt_to_equity"))),
                ("Debt/Equity (Tot.)",  r(s.get("total_debt_to_equity"))),
                ("Current Ratio",       r(s.get("current_ratio"))),
                ("Quick Ratio",         r(s.get("quick_ratio"))),
                ("Short Float",         p(s.get("float_short"))),
                ("52W High Dist.",      p(s.get("dist_from_52w_high"))),
                ("52W Low Dist.",       p(s.get("dist_from_52w_low"))),
            ]),
            ("PERFORMANCE", [
                ("Today",               p(s.get("perf_today"))),
                ("1 Week",              p(s.get("perf_week"))),
                ("1 Month",             p(s.get("perf_month"))),
                ("1 Quarter",           p(s.get("perf_quarter"))),
                ("6 Months",            p(s.get("perf_half_year"))),
                ("1 Year",              p(s.get("perf_year"))),
                ("YTD",                 p(s.get("perf_ytd"))),
            ]),
            ("OWNERSHIP & INFO", [
                ("Insider Ownership",   p(s.get("insider_ownership"))),
                ("Insider Trans.",      p(s.get("insider_transactions"))),
                ("Inst. Ownership",     p(s.get("inst_ownership"))),
                ("Inst. Trans.",        p(s.get("inst_transactions"))),
                ("Analyst Recom.",      r(s.get("analyst_recom"))),
                ("Avg Volume",          f"{int(s.get('average_volume') or 0):,}"),
                ("Earnings Date",       (s.get("earnings_date") or "—")[:10]),
                ("IPO Date",            (s.get("ipo_date") or "—")[:10]),
                ("Industry",            s.get("industry") or "—"),
                ("Country",             s.get("country") or "—"),
            ]),
        ]

        geo_facts = db.get_edgar_facts(s["stock_uid"], "geographic_revenue")
        if geo_facts:
            latest = geo_facts[-1]
            try:
                geo = json.loads(latest.get("value_json") or "{}")
                geo_rows = [
                    (k, f"{v * 100:.1f}%")
                    for k, v in sorted(geo.items(), key=lambda x: -x[1])
                ]
                sections.append(
                    (f"EDGAR GEOGRAPHIC REVENUE ({latest.get('period', '')})", geo_rows)
                )
            except Exception:
                pass

        parts: list[str] = []
        for title, rows in sections:
            parts.append(f"\n[bold cyan]{title}[/bold cyan]")
            for label, val in rows:
                parts.append(f"  [dim]{label:<28}[/dim]{val}")

        self.query_one("#qt-overview-content", Static).update("\n".join(parts))

    def _render_signals(self, s: dict) -> None:
        table = self.query_one("#qt-signals", DataTable)
        table.add_columns("Source", "Type", "Score", "Reason", "Date")

        signals = db.get_stock_signals(s["stock_uid"])
        events  = db.get_stock_events(s["stock_uid"])

        if not signals and not events:
            table.add_row("—", "No signals for this stock yet", "", "", "")
            return

        for sig in signals:
            score_str = (
                f"{sig['sub_score']:.0f}" if sig.get("sub_score") is not None else "—"
            )
            table.add_row(
                sig.get("source") or "—",
                sig.get("signal_type") or "—",
                score_str,
                (sig.get("reason") or "—")[:60],
                (sig.get("fetched_at") or "—")[:10],
            )

        for ev in events:
            role_style = "green" if ev.get("role") == "beneficiary" else "red"
            table.add_row(
                Text("Supply Chain", style="bold cyan"),
                Text(ev.get("role") or "—", style=role_style),
                "—",
                (ev.get("title") or "—")[:60],
                "",
            )

    def _render_history(self, s: dict) -> None:
        table = self.query_one("#qt-history", DataTable)
        table.add_columns("Date", "Open", "High", "Low", "Close", "Volume", "Dividend")

        start = (date.today() - timedelta(days=365)).isoformat()
        rows  = db.get_price_history(s["stock_uid"], start_date=start)

        if not rows:
            table.add_row("—", "No price history in DB", "", "", "", "", "")
            return

        for row in reversed(rows):
            div = row.get("dividend") or 0.0
            table.add_row(
                row.get("date") or "—",
                f"${row.get('open') or 0:.2f}",
                f"${row.get('high') or 0:.2f}",
                f"${row.get('low') or 0:.2f}",
                f"${row.get('close') or 0:.2f}",
                f"{int(row.get('volume') or 0):,}",
                f"${div:.4f}" if div > 0 else "—",
            )

    def _render_news(self, s: dict) -> None:
        articles = db.get_news_articles_for_stock(s["stock_uid"], limit=20)
        if not articles:
            self.query_one("#qt-news-content", Static).update(
                f"  No news articles for {self._ticker} in DB.\n\n"
                "  Run:  python src/news.py --watchlist   (add ticker to watchlist first)\n"
                "        python src/news.py --podcasts    (WSJ / Morgan Stanley / Motley Fool)"
            )
            return

        parts: list[str] = []
        for art in articles:
            source  = art.get("source") or "—"
            pub     = (art.get("published_at") or "—")[:10]
            title   = art.get("headline") or art.get("title") or "(no title)"
            summary = (art.get("summary") or "")[:140]
            parts.append(f"[bold cyan][{source}][/bold cyan]  [dim]{pub}[/dim]")
            parts.append(f"  {title}")
            if summary:
                parts.append(f"  [dim]{summary}[/dim]")
            parts.append("")

        self.query_one("#qt-news-content", Static).update("\n".join(parts))

    def _render_filings(self, s: dict) -> None:
        tbl    = self.query_one("#qt-filings-table", DataTable)
        ticker = s["ticker"]
        tbl.clear(columns=True)
        tbl.add_columns("Type", "File", "Size")

        cache_root = Path(FILINGS_CACHE_DIR)
        entries: list[tuple[str, Path]] = []
        for subdir in ("10k", "8k"):
            folder = cache_root / subdir
            if folder.exists():
                for f in sorted(folder.glob(f"{ticker}_*.txt")):
                    entries.append((subdir.upper(), f))

        if not entries:
            self.query_one("#qt-filing-text-content", Static).update(
                f"  No cached filings for {ticker}.\n\n"
                "  Run:  python src/edgar.py --fetch-filings   (10-K)\n"
                "        python src/edgar.py --fetch-8k         (8-K)"
            )
            return

        self._filing_paths: list[Path] = []
        for kind, path in entries:
            size_kb = path.stat().st_size // 1024
            tbl.add_row(kind, path.name, f"{size_kb} KB")
            self._filing_paths.append(path)

        self._show_filing(self._filing_paths[0])

    def _show_filing(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8")[:3000]
        except Exception as e:
            text = f"Could not read file: {e}"
        self.query_one("#qt-filing-text-content", Static).update(text)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "qt-filings-table":
            paths = getattr(self, "_filing_paths", [])
            idx   = list(event.data_table.rows.keys()).index(event.row_key)
            if 0 <= idx < len(paths):
                self._show_filing(paths[idx])
