"""
app.py — StackScreener desktop TUI (Textual).

Phase 1a: login screen, sidebar navigation, app shell.
Phase 1c: full Research sub-tabs — Screener, Calendar, Stock Comparison,
          Stock Picks, Research Reports.

Usage:
    python app.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button, Collapsible, DataTable, Footer, Header,
    Input, Label, Select, Static, TabbedContent, TabPane,
)

import db
from screener_config import (
    DEBUG_MODE,
    NEWS_WHISPER_MODEL,
    NEWS_SOURCE_WSJ_PODCAST,
    NEWS_SOURCE_WSJ_PDF,
    NEWS_SOURCE_MORGAN_STANLEY,
    NEWS_SOURCE_MOTLEY_FOOL,
    NEWS_SOURCE_YAHOO_FINANCE,
    PODCAST_FEEDS,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
    HEATMAP_DEFAULT_LIMIT, HEATMAP_LARGE_CAP_THRESHOLD,
    HEATMAP_MEGA_CAP_THRESHOLD, HEATMAP_SP500_LIMIT,
    FILINGS_CACHE_DIR,
    SCREENER_MCAP_BUCKETS, SCREENER_PE_BUCKETS,
    CALENDAR_EVENT_STYLES,
    SIGNAL_SOURCE_LABELS,
    HEATMAP_COLORS, HEATMAP_FILTERS,
)

# ── Formatting helpers ─────────────────────────────────────────────────────────

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


# ── Stock Quote Modal ─────────────────────────────────────────────────────────

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

    # ── header ─────────────────────────────────────────────────────────────────

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

    # ── overview ───────────────────────────────────────────────────────────────

    def _render_overview(self, s: dict) -> None:
        def p(v: float | None) -> str:
            return _fmt_pct(v) if v is not None else "—"

        def r(v: float | None, d: int = 2) -> str:
            return _fmt_ratio(v, d) if v is not None else "—"

        a = _fmt_pct_abs  # absolute-rate formatter: no leading + sign

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

        # Append EDGAR geographic revenue if available
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

    # ── signals ────────────────────────────────────────────────────────────────

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

    # ── price history ──────────────────────────────────────────────────────────

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

    # ── news ───────────────────────────────────────────────────────────────────

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

    # ── filings ────────────────────────────────────────────────────────────────

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

        # Show first filing by default
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


# ── Login screen ───────────────────────────────────────────────────────────────

class LoginScreen(Screen):
    CSS = """
    LoginScreen {
        align: center middle;
        background: $background;
    }
    #login-box {
        width: 50;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: solid $primary;
    }
    #app-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #app-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }
    #login-error {
        color: $error;
        text-align: center;
        height: 1;
        margin-top: 1;
    }
    .login-input { margin-bottom: 1; }
    #login-btn { width: 100%; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Label("STACKSCREENER", id="app-title"),
            Label("Supply Chain Intelligence", id="app-subtitle"),
            Input(placeholder="Username", id="username", classes="login-input"),
            Input(placeholder="Password", password=True, id="password", classes="login-input"),
            Button("Login", variant="primary", id="login-btn"),
            Label("", id="login-error"),
            id="login-box",
        )

    def on_mount(self) -> None:
        self.query_one("#username", Input).focus()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._do_login()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            self._do_login()

    def _do_login(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        error_label = self.query_one("#login-error", Label)
        if not username or not password:
            error_label.update("Username and password required.")
            return
        user = db.verify_user_password(username, password)
        if user is None:
            error_label.update("Invalid username or password.")
            self.query_one("#password", Input).value = ""
            self.query_one("#password", Input).focus()
            return
        self.app.current_user = user
        if user.get("force_password_change"):
            self.app.push_screen(ChangePasswordScreen())
        else:
            self.app.switch_screen(MainScreen())


# ── Password change screen ─────────────────────────────────────────────────────

class ChangePasswordScreen(Screen):
    CSS = """
    ChangePasswordScreen {
        align: center middle;
        background: $background;
    }
    #change-box {
        width: 52;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: solid $warning;
    }
    #change-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    #change-note {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }
    #change-error { color: $error; text-align: center; height: 1; margin-top: 1; }
    .change-input { margin-bottom: 1; }
    #change-btn { width: 100%; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Password Change Required", id="change-title"),
            Label("You must set a new password before continuing.", id="change-note"),
            Input(placeholder="New password", password=True, id="new-pass", classes="change-input"),
            Input(placeholder="Confirm new password", password=True, id="confirm-pass", classes="change-input"),
            Button("Set Password", variant="warning", id="change-btn"),
            Label("", id="change-error"),
            id="change-box",
        )

    def on_mount(self) -> None:
        self.query_one("#new-pass", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "change-btn":
            self._do_change()

    def _do_change(self) -> None:
        new_pass = self.query_one("#new-pass", Input).value
        confirm  = self.query_one("#confirm-pass", Input).value
        error    = self.query_one("#change-error", Label)
        if len(new_pass) < 8:
            error.update("Password must be at least 8 characters.")
            return
        if new_pass != confirm:
            error.update("Passwords do not match.")
            return
        db.update_password(self.app.current_user["user_uid"], new_pass)
        self.app.current_user["force_password_change"] = 0
        self.app.switch_screen(MainScreen())


# ── Sidebar ────────────────────────────────────────────────────────────────────

class NavItem(Static):
    can_focus = True

    def __init__(self, label: str, section: str, **kwargs) -> None:
        super().__init__(label, **kwargs)
        self.section = section

    def on_click(self) -> None:
        self.app.switch_section(self.section)

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.app.switch_section(self.section)


class Sidebar(Vertical):
    CSS = """
    Sidebar {
        width: 22;
        background: $surface-darken-1;
        border-right: solid $primary-darken-2;
        padding: 1 0;
    }
    #sidebar-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 0 1 1 1;
        border-bottom: solid $primary-darken-3;
        margin-bottom: 1;
    }
    NavItem { padding: 1 2; color: $text-muted; }
    NavItem:hover { background: $primary-darken-2; color: $text; }
    NavItem.active { background: $primary; color: $background; text-style: bold; }
    #ticker-search {
        margin: 1 1 0 1;
        width: 1fr;
    }
    #ticker-search-label {
        padding: 0 2;
        color: $text-muted;
        margin-top: 1;
    }
    #sidebar-user {
        dock: bottom;
        padding: 1 2;
        color: $text-muted;
        border-top: solid $primary-darken-3;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("STACKSCREENER", id="sidebar-title")
        yield NavItem("  HOME",      "home",      id="nav-home")
        yield NavItem("  RESEARCH",  "research",  id="nav-research")
        yield NavItem("  LOGISTICS", "logistics", id="nav-logistics")
        yield NavItem("  SETTINGS",  "settings",  id="nav-settings")
        yield Label("  Quote Search", id="ticker-search-label")
        yield Input(placeholder="Ticker… (Enter)", id="ticker-search")
        user = getattr(self.app, "current_user", None)
        name = (user.get("display_name") or user.get("username")) if user else ""
        yield Label(f"  {name}", id="sidebar-user")

    def on_input_submitted(self, event) -> None:
        if event.input.id != "ticker-search":
            return
        ticker = event.value.strip().upper()
        event.input.value = ""
        if ticker:
            self.app.push_screen(StockQuoteModal(ticker))

    def set_active(self, section: str) -> None:
        for item in self.query(NavItem):
            item.remove_class("active")
        nav = self.query(f"#nav-{section}")
        if nav:
            nav.first(NavItem).add_class("active")


# ══════════════════════════════════════════════════════════════════════════════
#  RESEARCH SUB-TABS
# ══════════════════════════════════════════════════════════════════════════════

# ── Screener tab ───────────────────────────────────────────────────────────────

_SIGNAL_FILTERS = {
    "All Stocks":         lambda r: True,
    "Supply Chain Picks": lambda r: (r.get("score_supply_chain") or 0) >= 20,
    "Congress Buys":      lambda r: (r.get("score_inst_flow") or 0) >= 50,
}


class ScreenerTab(Vertical):
    CSS = """
    ScreenerTab { height: 1fr; }
    #scr-filters {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $border;
        padding: 0 1;
    }
    #scr-note { color: $text-muted; padding: 0 1; height: 1; }
    #scr-table { height: 1fr; }
    Select { width: 18; margin-right: 1; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="scr-filters"):
            yield Select(
                [("Exchange: Any", ""), ("NASDAQ", "NASDAQ"), ("NYSE", "NYSE"), ("NYSE ARCA", "NYSE ARCA")],
                value="", id="scr-exchange", allow_blank=False,
            )
            yield Select(
                [("Sector: Any", "")], value="", id="scr-sector", allow_blank=False,
            )
            yield Select(
                [("MCap: Any", ""), *[(k, k) for k in SCREENER_MCAP_BUCKETS]],
                value="", id="scr-mcap", allow_blank=False,
            )
            yield Select(
                [("P/E: Any", ""), *[(k, k) for k in SCREENER_PE_BUCKETS]],
                value="", id="scr-pe", allow_blank=False,
            )
            yield Select(
                [(k, k) for k in _SIGNAL_FILTERS],
                value="All Stocks", id="scr-signal", allow_blank=False,
            )
        yield Label("", id="scr-note")
        yield DataTable(id="scr-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("#", "Ticker", "Company", "Sector", "MCap", "P/E", "Price", "Score")
        self._all_results: list[dict] = []
        self._load_results()

    def _load_results(self) -> None:
        scans = db.get_recent_scans(1)
        if not scans:
            self.query_one("#scr-note", Label).update("No scans yet. Run: python screener_run.py")
            return
        scan = scans[0]
        self._all_results = db.get_scan_results(scan["scan_uid"], limit=2000)
        # populate sector filter dynamically
        sectors = sorted({r.get("sector") or "" for r in self._all_results if r.get("sector")})
        sel = self.query_one("#scr-sector", Select)
        sel.set_options([("Sector: Any", ""), *[(s, s) for s in sectors]])
        self.query_one("#scr-note", Label).update(
            f"Scan #{scan['scan_uid']}  mode={scan['scan_mode']}  "
            f"scored={scan.get('scored_count') or 0}  "
            f"at {(scan.get('started_at') or '')[:19]}"
            f"   ↑↓ navigate  Enter=quote"
        )
        self._repopulate()

    def on_select_changed(self, _event: Select.Changed) -> None:
        self._repopulate()

    def _repopulate(self) -> None:
        exchange = self.query_one("#scr-exchange", Select).value or ""
        sector   = self.query_one("#scr-sector",   Select).value or ""
        mcap_key = self.query_one("#scr-mcap",     Select).value or ""
        pe_key   = self.query_one("#scr-pe",       Select).value or ""
        sig_key  = str(self.query_one("#scr-signal", Select).value or "All Stocks")

        mcap_min = SCREENER_MCAP_BUCKETS.get(mcap_key, 0) if mcap_key else 0
        mcap_max = (
            SCREENER_MCAP_BUCKETS.get(list(SCREENER_MCAP_BUCKETS.keys())[
                list(SCREENER_MCAP_BUCKETS.keys()).index(mcap_key) - 1
            ], 9e18) if mcap_key and list(SCREENER_MCAP_BUCKETS.keys()).index(mcap_key) > 0 else 9e18
        ) if mcap_key else 9e18
        pe_range = SCREENER_PE_BUCKETS.get(pe_key) if pe_key else None
        sig_fn   = _SIGNAL_FILTERS.get(sig_key, lambda r: True)

        filtered = [
            r for r in self._all_results
            if (not exchange or r.get("exchange") == exchange)
            and (not sector or r.get("sector") == sector)
            and (not mcap_key or mcap_min <= (r.get("market_cap_at_scan") or 0) < mcap_max)
            and (not pe_range or pe_range[0] <= (r.get("score_pe") or 0) < pe_range[1])
            and sig_fn(r)
        ]

        table = self.query_one(DataTable)
        table.clear()
        for r in filtered[:200]:
            score = r.get("composite_score") or 0
            bar_color = "green" if score > 70 else "yellow" if score > 50 else "red"
            score_cell = Text(f"{_score_bar(score)} {score:.0f}", style=bar_color)
            table.add_row(
                str(r.get("composite_rank") or ""),
                r.get("ticker") or "",
                (r.get("company_name") or r.get("ticker") or "")[:28],
                (r.get("sector") or "")[:24],
                _fmt_mcap(r.get("market_cap_at_scan")),
                _fmt_ratio(r.get("score_pe") / 100 * 50 if r.get("score_pe") else None),
                f"${r.get('price_at_scan') or 0:.2f}",
                score_cell,
                key=r.get("ticker") or "",
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        ticker = str(event.row_key.value) if event.row_key and event.row_key.value else ""
        if ticker:
            self.app.push_screen(StockQuoteModal(ticker))


# ── Calendar tab ───────────────────────────────────────────────────────────────


_FILTER_TO_ETYPE: dict[str, str | list[str] | None] = {
    "all":       None,
    "earnings":  "earnings",
    "splits":    "split",
    "ipos":      "ipo",
    "economic":  "economic",
    "dividends": ["ex_dividend", "dividend_pay"],
}


class DayCell(Static):
    DEFAULT_CSS = """
    DayCell {
        width: 1fr;
        height: 100%;
        border: solid $border;
        padding: 0 1;
        overflow-y: hidden;
    }
    DayCell.today { border: solid $primary; background: $surface-darken-1; }
    """

    def set_day(self, day: date, events: list[dict], is_today: bool) -> None:
        text = Text()
        text.append(day.strftime("%a"), style="bold")
        text.append(f"\n{day.strftime('%b %d')}", style="dim")
        text.append("\n")
        for ev in events[:5]:
            etype = ev.get("event_type", "")
            style = CALENDAR_EVENT_STYLES.get(etype, "white")
            title = (ev.get("title") or "")[:14]
            text.append(f"\n{title}", style=style)
        self.update(text)
        if is_today:
            self.add_class("today")
        else:
            self.remove_class("today")


class CalendarTab(Vertical):
    CSS = """
    CalendarTab { height: 1fr; }
    #cal-nav {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $border;
        padding: 0 1;
        align: left middle;
    }
    #week-label { width: 22; content-align: center middle; }
    .cal-filter { min-width: 10; margin-left: 1; }
    .cal-filter.active { background: $primary; color: $background; }
    #week-grid { height: 14; border-bottom: solid $border; }
    #cal-detail { height: 1fr; }
    """

    _week_offset: reactive[int] = reactive(0)
    _event_filter: reactive[str] = reactive("all")

    def compose(self) -> ComposeResult:
        with Horizontal(id="cal-nav"):
            yield Button("◀", id="btn-prev-wk", variant="default")
            yield Label("", id="week-label")
            yield Button("▶", id="btn-next-wk", variant="default")
            for lbl, key in [("All", "all"), ("Earnings", "earnings"), ("Splits", "splits"),
                              ("IPOs", "ipos"), ("Economic", "economic"), ("Dividends", "dividends")]:
                yield Button(lbl, id=f"cal-f-{key}", classes="cal-filter")
        with Horizontal(id="week-grid"):
            for i in range(7):
                yield DayCell(id=f"day-{i}")
        yield DataTable(id="cal-detail", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Ticker", "Event", "Date", "Details")
        self.query_one("#cal-f-all", Button).add_class("active")
        db.sync_dividend_calendar_events()
        self._refresh()

    def watch__week_offset(self, _: int) -> None:
        self._refresh()

    def watch__event_filter(self, _: str) -> None:
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "btn-prev-wk":
            self._week_offset -= 1
        elif bid == "btn-next-wk":
            self._week_offset += 1
        elif bid.startswith("cal-f-"):
            key = bid[6:]
            self._event_filter = key
            for btn in self.query(".cal-filter"):
                btn.remove_class("active")
            event.button.add_class("active")

    def _refresh(self) -> None:
        days = _week_dates(self._week_offset)
        today = date.today()
        start = days[0].strftime("%Y-%m-%d")
        end   = days[6].strftime("%Y-%m-%d")
        etype = _FILTER_TO_ETYPE.get(self._event_filter)
        events = db.get_calendar_events_with_ticker(start, end, event_type=etype)

        self.query_one("#week-label", Label).update(
            f" {days[0].strftime('%b %d')} – {days[6].strftime('%b %d, %Y')} "
        )

        by_date: dict[str, list[dict]] = {}
        for ev in events:
            by_date.setdefault(ev["event_date"], []).append(ev)

        for i, day in enumerate(days):
            cell = self.query_one(f"#day-{i}", DayCell)
            cell.set_day(day, by_date.get(day.strftime("%Y-%m-%d"), []), day == today)

        table = self.query_one(DataTable)
        table.clear()
        for ev in sorted(events, key=lambda e: e["event_date"]):
            ticker = ev.get("ticker") or "—"
            detail = ""
            if ev.get("eps_estimate"):
                detail = f"EPS Est: ${ev['eps_estimate']:.2f}"
            elif ev.get("ipo_price_low"):
                hi = ev.get("ipo_price_high")
                detail = f"Range: ${ev['ipo_price_low']:.0f}–${hi:.0f}" if hi else f"${ev['ipo_price_low']:.0f}"
            elif ev.get("split_ratio"):
                detail = f"Ratio: {ev['split_ratio']}"
            elif ev.get("event_type") in ("ex_dividend", "dividend_pay"):
                detail = str(ev.get("detail") or "")[:50]
            elif ev.get("detail"):
                detail = str(ev["detail"])[:50]
            table.add_row(ticker, ev.get("title") or "", ev.get("event_date") or "", detail)


# ── Stock Comparison tab ───────────────────────────────────────────────────────

_CMP_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Valuation", [
        ("Market Cap",    "market_cap"),
        ("P/E Ratio",     "pe_ratio"),
        ("EV/Revenue",    "ev_revenue"),
        ("EV/EBITDA",     "ev_ebitda"),
        ("PEG Ratio",     "peg_ratio"),
        ("P/B Ratio",     "pb_ratio"),
    ]),
    ("Income & Margins", [
        ("Gross Margin",    "gross_margin"),
        ("Operating Margin","operating_margin"),
        ("Net Margin",      "net_profit_margin"),
        ("ROE",             "return_on_equity"),
        ("ROA",             "return_on_assets"),
    ]),
    ("Risk & Performance", [
        ("Beta",            "beta"),
        ("D/E Ratio",       "total_debt_to_equity"),
        ("1 Week",          "perf_week"),
        ("1 Month",         "perf_month"),
        ("1 Year",          "perf_year"),
        ("YTD",             "perf_ytd"),
    ]),
]

_PCT_FIELDS = frozenset({
    "gross_margin", "operating_margin", "net_profit_margin",
    "return_on_equity", "return_on_assets",
    "perf_week", "perf_month", "perf_year", "perf_ytd",
})


def _fmt_cmp_val(field: str, v: float | None) -> str:
    if v is None:
        return "—"
    if field == "market_cap":
        return _fmt_mcap(v)
    if field in _PCT_FIELDS:
        return _fmt_pct(v)
    return _fmt_ratio(v)


class StockComparisonTab(Vertical):
    CSS = """
    StockComparisonTab { height: 1fr; }
    #cmp-inputs {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $border;
        padding: 0 1;
        align: left middle;
    }
    .cmp-input { width: 12; margin-right: 1; }
    #btn-compare { margin-left: 1; }
    #cmp-note { color: $text-muted; padding: 0 1; height: 1; }
    #cmp-table { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="cmp-inputs"):
            for i in range(1, 5):
                yield Input(placeholder=f"Ticker {i}", id=f"cmp-t{i}", classes="cmp-input")
            yield Button("Compare", variant="primary", id="btn-compare")
        yield Label("Enter up to 4 tickers and press Compare.", id="cmp-note")
        yield DataTable(id="cmp-table")

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("Metric", "Ticker 1", "Ticker 2", "Ticker 3", "Ticker 4")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-compare":
            self._compare()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self._compare()

    def _compare(self) -> None:
        tickers = [
            self.query_one(f"#cmp-t{i}", Input).value.strip().upper()
            for i in range(1, 5)
        ]
        tickers = [t for t in tickers if t]
        if not tickers:
            self.query_one("#cmp-note", Label).update("Enter at least one ticker.")
            return

        stock_map = db.get_stocks_by_tickers(tickers)
        stocks = [stock_map.get(t) for t in tickers]
        names = [
            (s.get("company_name") or s["ticker"]) if s else f"({t} not found)"
            for s, t in zip(stocks, tickers)
        ]

        table = self.query_one(DataTable)
        # DataTable.clear() removes rows but keeps columns; remove+remount to reset columns
        table.remove()
        table = DataTable(id="cmp-table")
        self.mount(table)
        table.add_columns("Metric", *names)

        today = date.today()
        self.query_one("#cmp-note", Label).update(
            f"Comparing {', '.join(t for t in tickers)}  •  {today.strftime('%b %d, %Y')}"
        )

        for section_name, metrics in _CMP_SECTIONS:
            table.add_row(f"[bold]{section_name}[/bold]", *[""] * len(tickers), key=f"__sec_{section_name}")
            for label, field in metrics:
                vals = [s.get(field) if s else None for s in stocks]
                # pad to 4
                while len(vals) < 4:
                    vals.append(None)
                fmt_vals = [_fmt_cmp_val(field, v) for v in vals[:len(tickers)]]

                # highlight best/worst (numeric only)
                numeric = [(i, v) for i, v in enumerate(vals[:len(tickers)]) if v is not None]
                row_cells: list[str | Text] = [label]
                if len(numeric) >= 2:
                    higher_better = field not in {
                        "pe_ratio", "ev_revenue", "ev_ebitda", "peg_ratio",
                        "pb_ratio", "beta", "total_debt_to_equity",
                    }
                    best_idx = max(numeric, key=lambda x: x[1])[0] if higher_better else min(numeric, key=lambda x: x[1])[0]
                    worst_idx = min(numeric, key=lambda x: x[1])[0] if higher_better else max(numeric, key=lambda x: x[1])[0]
                    for i, fv in enumerate(fmt_vals):
                        if i == best_idx:
                            row_cells.append(Text(f"▲ {fv}", style="green bold"))
                        elif i == worst_idx:
                            row_cells.append(Text(f"▼ {fv}", style="red"))
                        else:
                            row_cells.append(fv)
                else:
                    row_cells.extend(fmt_vals)
                # pad to 4 data columns
                while len(row_cells) < 5:
                    row_cells.append("")
                table.add_row(*row_cells[:5])


# ── Stock Picks tab ────────────────────────────────────────────────────────────


class StockPicksTab(ScrollableContainer):
    CSS = """
    StockPicksTab {
        padding: 1;
        height: 1fr;
    }
    #picks-note {
        color: $text-muted;
        margin-bottom: 1;
        padding: 0 1;
    }
    Collapsible { margin-bottom: 1; }
    .pick-detail { padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="picks-note")

    def on_mount(self) -> None:
        self._load_picks()

    def _load_picks(self) -> None:
        # Remove any cards from a previous load before mounting new ones.
        for old in self.query(Collapsible):
            old.remove()

        scans = db.get_recent_scans(1)
        if not scans:
            self.query_one("#picks-note", Label).update(
                "No scan results yet. Run: python screener_run.py"
            )
            return

        top = db.get_scan_results(scans[0]["scan_uid"], limit=15)
        self.query_one("#picks-note", Label).update(
            f"Top picks from scan #{scans[0]['scan_uid']}  "
            f"(Phase 3 will add congressional/insider signal cards)"
        )

        for pick in top:
            score = pick.get("composite_score") or 0
            sc    = pick.get("score_supply_chain") or 0
            ticker = pick.get("ticker") or ""
            company = pick.get("company_name") or ticker
            price  = pick.get("price_at_scan") or 0
            title = (
                f"{ticker} — {company[:24]}   "
                f"${price:.2f}   Score: {score:.1f}"
            )
            signals = db.get_stock_signals(pick["stock_uid"])
            card = Collapsible(title=title, collapsed=True)
            with card:
                yield self._make_pick_detail(pick, signals)
                yield Button("Open Quote →", id=f"btn-quote-{ticker}", variant="default")
            self.mount(card)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("btn-quote-"):
            self.app.push_screen(StockQuoteModal(bid.removeprefix("btn-quote-")))

    def _make_pick_detail(self, pick: dict, signals: list[dict]) -> Static:
        lines: list[str] = [
            f"  Composite: {pick.get('composite_score', 0):.1f}  |  "
            f"SC Bonus: {pick.get('score_supply_chain', 0):.0f}  |  "
            f"Flow Bonus: {pick.get('score_inst_flow', 0):.0f}",
            f"  EV/R: {pick.get('score_ev_revenue', 0):.0f}  "
            f"PE: {pick.get('score_pe', 0):.0f}  "
            f"EV/EBITDA: {pick.get('score_ev_ebitda', 0):.0f}  "
            f"Margin: {pick.get('score_profit_margin', 0):.0f}  "
            f"D/E: {pick.get('score_debt_equity', 0):.0f}",
            "",
        ]
        if signals:
            lines.append("  Source Signals:")
            for sig in signals[:6]:
                src  = SIGNAL_SOURCE_LABELS.get(sig.get("source") or "", sig.get("source") or "")
                sub  = sig.get("sub_score")
                sub_str = f"{sub:.0f}" if sub is not None else "—"
                reason = (sig.get("reason_text") or "")[:60]
                lines.append(f"    [{src:<18}] {sub_str:>4}  {reason}")
        else:
            lines.append("  No source signals yet — will populate in Phase 3 (inst flow).")
        return Static("\n".join(lines), classes="pick-detail")


# ── News tab ──────────────────────────────────────────────────────────────────

_NEWS_FILTER_LABELS: list[tuple[str, str | None]] = [
    ("All",           None),
    ("WSJ Podcast",   NEWS_SOURCE_WSJ_PODCAST),
    ("WSJ PDF",       NEWS_SOURCE_WSJ_PDF),
    ("Morgan Stanley",NEWS_SOURCE_MORGAN_STANLEY),
    ("Motley Fool",   NEWS_SOURCE_MOTLEY_FOOL),
    ("Yahoo Finance", NEWS_SOURCE_YAHOO_FINANCE),
]

_NEWS_SOURCE_DISPLAY: dict[str, str] = {
    NEWS_SOURCE_WSJ_PODCAST:    "WSJ Podcast",
    NEWS_SOURCE_WSJ_PDF:        "WSJ PDF",
    NEWS_SOURCE_MORGAN_STANLEY: "Morgan Stanley",
    NEWS_SOURCE_MOTLEY_FOOL:    "Motley Fool",
    NEWS_SOURCE_YAHOO_FINANCE:  "Yahoo Finance",
}


class NewsTab(Vertical):
    CSS = """
    NewsTab { height: 1fr; }
    #news-filters {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $border;
        padding: 0 1;
        align: left middle;
    }
    .news-filter { min-width: 13; margin-right: 1; }
    .news-filter.active { background: $primary; color: $background; }
    #news-note { color: $text-muted; padding: 0 1; height: 1; }
    #news-table { height: 1fr; }
    """

    _active_source: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Horizontal(id="news-filters"):
            for label, source in _NEWS_FILTER_LABELS:
                fid = f"nf-{(source or 'all').replace('_', '-')}"
                yield Button(label, id=fid, classes="news-filter")
        yield Label("", id="news-note")
        yield DataTable(id="news-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Date", "Source", "Ticker", "Headline")
        self.query_one("#nf-all", Button).add_class("active")
        self._load()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if not bid.startswith("nf-"):
            return
        for btn in self.query(".news-filter"):
            btn.remove_class("active")
        event.button.add_class("active")
        # Map button id back to source value
        for label, source in _NEWS_FILTER_LABELS:
            fid = f"nf-{(source or 'all').replace('_', '-')}"
            if fid == bid:
                self._active_source = source
                break

    def watch__active_source(self, _: str | None) -> None:
        self._load()

    def _load(self) -> None:
        articles = db.get_news_articles(source=self._active_source, limit=100)
        table = self.query_one(DataTable)
        table.clear()
        if not articles:
            self.query_one("#news-note", Label).update(
                "No articles yet.  Run: python src/news.py --all"
            )
            return
        self.query_one("#news-note", Label).update(
            f"{len(articles)} article(s)"
            + (f" — {_NEWS_SOURCE_DISPLAY.get(self._active_source, self._active_source)}" if self._active_source else "")
        )
        for art in articles:
            pub      = (art.get("published_at") or "")[:10]
            src      = _NEWS_SOURCE_DISPLAY.get(art.get("source") or "", art.get("source") or "")
            headline = (art.get("headline") or "")[:80]
            ticker   = art.get("ticker") or "—"
            table.add_row(pub, src, ticker, headline)


# ── Research Reports tab ───────────────────────────────────────────────────────

_TAG_STYLE: dict[str, str] = {
    "supply_chain": "yellow",
    "fundamentals": "green",
    "inst_flow":    "cyan",
}


class ResearchReportsTab(ScrollableContainer):
    CSS = """
    ResearchReportsTab {
        padding: 1;
        height: 1fr;
    }
    .report-card {
        border: solid $border;
        padding: 1 2;
        margin-bottom: 1;
    }
    .report-card:hover { border: solid $primary; }
    #rpt-empty { color: $text-muted; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="rpt-empty")

    def on_mount(self) -> None:
        self._load_reports()

    def _load_reports(self) -> None:
        reports = db.get_research_reports(limit=20)
        if not reports:
            self.query_one("#rpt-empty", Label).update(
                "No research reports yet.\n\n"
                "Reports are generated from supply chain events, EDGAR data,\n"
                "and institutional flow signals. They will appear here as\n"
                "Phase 2 (Supply Chain Signal Engine) is built out."
            )
            return
        self.query_one("#rpt-empty", Label).update("")
        for rpt in reports:
            tag = rpt.get("tag") or "fundamentals"
            tag_style = _TAG_STYLE.get(tag, "white")
            tag_label = tag.replace("_", " ").title()
            pub = (rpt.get("published_at") or "")[:10]
            title   = rpt.get("title") or ""
            summary = rpt.get("summary") or ""
            text = Text()
            text.append(f"[{tag_label}]", style=f"bold {tag_style}")
            text.append(f"  {pub}\n", style="dim")
            text.append(f"{title}\n", style="bold")
            text.append(summary, style="dim")
            card = Static(text, classes="report-card")
            self.mount(card)


# ══════════════════════════════════════════════════════════════════════════════
#  CONTENT PANELS
# ══════════════════════════════════════════════════════════════════════════════

# ── Heatmap tile ───────────────────────────────────────────────────────────────


def _heat_bg(pct: float | None) -> str:
    if pct is None:
        return "#1a1a1a"
    for threshold, color in HEATMAP_COLORS:
        if pct >= threshold:
            return color
    return HEATMAP_COLORS[-1][1]


class HeatmapTile(Static):
    """Single stock tile in the home heatmap grid."""

    can_focus = True

    DEFAULT_CSS = """
    HeatmapTile {
        width: 1fr;
        height: 4;
        padding: 0 1;
        content-align: left top;
    }
    HeatmapTile:focus { border: solid $primary; }
    HeatmapTile:hover { opacity: 0.85; }
    """

    def __init__(self, stock: dict, **kwargs) -> None:
        self._stock   = stock
        self._ticker  = stock["ticker"]
        pct           = stock.get("change_pct") or 0.0
        sign          = "+" if pct >= 0 else ""
        lines = [
            f" {self._ticker[:8]}",
            f" {sign}{pct:.1f}%",
            f" {_fmt_mcap(stock.get('market_cap'))}",
        ]
        super().__init__("\n".join(lines), **kwargs)

    def on_mount(self) -> None:
        self.styles.background = _heat_bg(self._stock.get("change_pct"))

    def on_click(self) -> None:
        self.app.push_screen(StockQuoteModal(self._ticker))

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.app.push_screen(StockQuoteModal(self._ticker))


# ── World map ──────────────────────────────────────────────────────────────────

_MAP_W = 74
_MAP_H = 18


def _build_base_map() -> list[list[str]]:
    """Build 74×18 equirectangular ASCII base map (1 col≈5°lon, 1 row≈10°lat)."""
    grid: list[list[str]] = [[" "] * _MAP_W for _ in range(_MAP_H)]

    def fill(c0: int, c1: int, r0: int, r1: int) -> None:
        for r in range(max(0, r0), min(_MAP_H, r1 + 1)):
            for c in range(max(0, c0), min(_MAP_W, c1 + 1)):
                grid[r][c] = "~"

    # North America
    fill(3,  9,  1, 2)    # Alaska
    fill(7,  22, 2, 7)    # Canada + US
    fill(12, 17, 6, 8)    # Mexico
    fill(14, 18, 7, 8)    # C. America
    fill(15, 23, 8, 13)   # South America
    fill(16, 19, 13, 14)  # Patagonia
    fill(22, 30, 0, 2)    # Greenland
    # Europe
    fill(33, 36, 2, 4)    # UK/Ireland
    fill(35, 43, 1, 2)    # Scandinavia
    fill(36, 44, 2, 5)    # W/C Europe
    # Africa + Middle East
    fill(32, 47, 5, 10)   # N Africa / Sahara
    fill(38, 51, 4, 5)    # Turkey / Caucasus
    fill(40, 51, 5, 9)    # Arabia / NE Africa
    fill(40, 50, 9, 14)   # C + S Africa
    fill(51, 53, 10, 12)  # Madagascar
    # Russia / Eurasia
    fill(42, 74, 0, 4)    # Russia / Siberia
    fill(44, 66, 4, 5)    # Central Asia
    # India
    fill(50, 57, 5, 9)    # Indian subcontinent
    # China + East Asia
    fill(52, 68, 3, 7)    # China
    fill(64, 72, 3, 6)    # Korea + Japan
    # SE Asia + Indonesia
    fill(57, 68, 7, 11)   # Indochina / SE Asia
    fill(61, 68, 9, 11)   # Borneo
    fill(60, 66, 10, 11)  # Java
    # Australia + NZ
    fill(60, 71, 10, 15)  # Australia
    fill(70, 73, 13, 15)  # New Zealand

    return grid


_BASE_MAP_GRID: list[list[str]] = _build_base_map()


def _latlon_to_xy(lat: float, lon: float) -> tuple[int, int]:
    x = int((lon + 180) / 360 * _MAP_W)
    y = int((90  - lat) / 180 * _MAP_H)
    return (max(0, min(_MAP_W - 1, x)), max(0, min(_MAP_H - 1, y)))


class WorldMap(Static):
    """ASCII equirectangular world map with coloured event markers."""

    DEFAULT_CSS = """
    WorldMap {
        height: 20;
        padding: 0 1;
        border-bottom: solid $border;
        background: $surface-darken-2;
    }
    """

    def __init__(self, events: list[dict], **kwargs) -> None:
        super().__init__("", **kwargs)
        self._events = events

    def on_mount(self) -> None:
        self._draw_map()

    def update_events(self, events: list[dict]) -> None:
        self._events = events
        self._draw_map()

    def _draw_map(self) -> None:
        grid = [list(row) for row in _BASE_MAP_GRID]

        marker_map: dict[tuple[int, int], str] = {}
        for ev in self._events:
            lat = ev.get("lat")
            lon = ev.get("lon")
            if lat is None or lon is None:
                continue
            x, y   = _latlon_to_xy(float(lat), float(lon))
            sev    = ev.get("severity") or ""
            color  = _SEVERITY_COLOR.get(sev, "white")
            marker_map[(y, x)] = color

        text = Text()
        for r, row in enumerate(grid):
            for c, char in enumerate(row):
                marker_color = marker_map.get((r, c))
                if marker_color:
                    text.append("●", style=f"bold {marker_color}")
                elif char == "~":
                    text.append(char, style="dim green")
                else:
                    text.append(char)
            text.append("\n")

        # Legend line
        for sev, color in _SEVERITY_COLOR.items():
            text.append(f" ● {sev}", style=f"bold {color}")
        text.append("\n")

        self.update(text)


# ── Home panel ─────────────────────────────────────────────────────────────────


class HomePanel(Vertical):
    CSS = """
    HomePanel { height: 1fr; padding: 0; }
    #home-stats {
        height: auto;
        padding: 0 2;
        color: $text-muted;
        background: $surface-darken-1;
        border-bottom: solid $border;
    }
    #home-filter-row {
        height: 3;
        padding: 0 1;
        background: $surface-darken-1;
        border-bottom: solid $border;
    }
    #home-filter-row Button { margin-right: 1; min-width: 12; height: 2; }
    #heatmap-scroller { height: 1fr; }
    #heatmap-grid {
        layout: grid;
        grid-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
        padding: 1;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Loading…", id="home-stats")
        with Horizontal(id="home-filter-row"):
            for label, btn_id in HEATMAP_FILTERS:
                variant = "primary" if label == "All" else "default"
                yield Button(label, id=btn_id, variant=variant)
        with ScrollableContainer(id="heatmap-scroller"):
            yield Container(id="heatmap-grid")

    def on_mount(self) -> None:
        self._load_stats()
        self._load_heatmap("All")

    def _load_stats(self) -> None:
        try:
            scans    = db.get_recent_scans(1)
            events   = db.get_active_events()
            total    = db.get_active_stock_count()
            enriched = db.get_enriched_stock_count()
            last_scan = scans[0] if scans else None
            parts = [
                f"Stocks: {total} active",
                f"  Enriched: {enriched}",
                f"  SC events: {len(events)}",
            ]
            if last_scan:
                parts.append(
                    f"  Last scan #{last_scan['scan_uid']}"
                    f"  mode={last_scan['scan_mode']}"
                    f"  scored={last_scan.get('scored_count') or 0}"
                    f"  {(last_scan.get('started_at') or '')[:10]}"
                )
            self.query_one("#home-stats", Static).update("  " + "  |  ".join(parts))
        except Exception as e:
            self.query_one("#home-stats", Static).update(f"  Error: {e}")

    def _load_heatmap(self, mode: str) -> None:
        limit        = HEATMAP_DEFAULT_LIMIT
        min_mcap     = None
        watchlist_only = False
        match mode:
            case "Large Cap": min_mcap = HEATMAP_LARGE_CAP_THRESHOLD
            case "Mega Cap":  min_mcap = HEATMAP_MEGA_CAP_THRESHOLD
            case "S&P ≈500":  limit    = HEATMAP_SP500_LIMIT
            case "Watchlist": watchlist_only = True

        stocks = db.get_heatmap_stocks(limit=limit, min_mcap=min_mcap, watchlist_only=watchlist_only)
        grid   = self.query_one("#heatmap-grid", Container)
        grid.remove_children()

        # Highlight active filter button
        for label, btn_id in HEATMAP_FILTERS:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.variant = "primary" if label == mode else "default"
            except Exception:
                pass

        if not stocks:
            grid.mount(Label("  No change data yet — run: python src/enricher.py"))
            return

        for stock in stocks:
            grid.mount(HeatmapTile(stock))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "hf-all":      self._load_heatmap("All")
            case "hf-largecap": self._load_heatmap("Large Cap")
            case "hf-megacap":  self._load_heatmap("Mega Cap")
            case "hf-sp500":    self._load_heatmap("S&P ≈500")
            case "hf-watchlist":self._load_heatmap("Watchlist")


class ResearchPanel(Vertical):
    CSS = """
    ResearchPanel { padding: 0; height: 1fr; }
    TabbedContent { height: 1fr; }
    TabPane { height: 1fr; padding: 0; }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent(id="research-tabs"):
            with TabPane("Screener", id="tab-screener"):
                yield ScreenerTab()
            with TabPane("Calendar", id="tab-calendar"):
                yield CalendarTab()
            with TabPane("Stock Comparison", id="tab-comparison"):
                yield StockComparisonTab()
            with TabPane("Stock Picks", id="tab-picks"):
                yield StockPicksTab()
            with TabPane("Research Reports", id="tab-reports"):
                yield ResearchReportsTab()
            with TabPane("News", id="tab-news"):
                yield NewsTab()


_SEVERITY_COLOR: dict[str, str] = {
    SEVERITY_CRITICAL: "red",
    SEVERITY_HIGH:     "dark_orange",
    SEVERITY_MEDIUM:   "yellow",
    SEVERITY_LOW:      "blue",
}


class EventListItem(Static):
    """Clickable row in the Logistics event list."""

    can_focus = True

    class Selected(Message):
        def __init__(self, uid: int) -> None:
            self.uid = uid
            super().__init__()

    DEFAULT_CSS = """
    EventListItem {
        padding: 0 1;
        height: 3;
        border-bottom: solid $border;
    }
    EventListItem:hover { background: $primary-darken-2; }
    EventListItem:focus  { background: $primary-darken-1; }
    EventListItem.selected { background: $primary; color: $background; }
    """

    def __init__(self, event: dict, **kwargs) -> None:
        self._uid      = event["supply_chain_event_uid"]
        self._severity = event.get("severity") or ""
        color          = _SEVERITY_COLOR.get(self._severity, "white")
        region         = (event.get("region") or "")[:22]
        title          = (event.get("title") or "")[:26]
        text = Text()
        text.append(f"[{self._severity[:3]}] ", style=f"bold {color}")
        text.append(region + "\n", style="bold")
        text.append(title, style="dim")
        super().__init__(text, **kwargs)

    def on_click(self) -> None:
        self.post_message(self.Selected(self._uid))

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.post_message(self.Selected(self._uid))


class LogisticsPanel(Vertical):
    CSS = """
    LogisticsPanel { height: 1fr; }
    #logi-header {
        height: 2;
        background: $surface-darken-1;
        border-bottom: solid $border;
        padding: 0 1;
        align: left middle;
    }
    #logi-header Label { color: $primary; text-style: bold; }
    #logi-body { height: 1fr; }
    #logi-event-list {
        width: 34;
        border-right: solid $border;
        overflow-y: auto;
    }
    #logi-right { width: 1fr; height: 1fr; }
    #logi-map-wrap {
        height: 22;
        border-bottom: solid $border;
        overflow: hidden;
    }
    #logi-detail {
        height: 7;
        padding: 1 2;
        background: $surface-darken-1;
        border-bottom: solid $border;
        color: $text-muted;
    }
    #logi-companies { height: 1fr; }
    """

    _selected_uid: reactive[int | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Horizontal(id="logi-header"):
            yield Label("LOGISTICS — Active Supply Chain Events")
        with Horizontal(id="logi-body"):
            yield ScrollableContainer(id="logi-event-list")
            with Vertical(id="logi-right"):
                yield Container(id="logi-map-wrap")
                yield Static("Select an event from the list.", id="logi-detail")
                yield DataTable(id="logi-companies", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#logi-companies", DataTable)
        table.add_columns("Role", "Ticker", "Sector", "Cannot Provide", "Will Redirect To", "Confidence")
        self._load_events()

    def _load_events(self) -> None:
        events     = db.get_active_events()
        event_list = self.query_one("#logi-event-list", ScrollableContainer)
        map_wrap   = self.query_one("#logi-map-wrap", Container)

        event_list.remove_children()
        map_wrap.remove_children()

        map_wrap.mount(WorldMap(events, id="logi-world-map"))

        if not events:
            event_list.mount(Label("  No active supply chain events.", id="logi-empty"))
            return
        for ev in events:
            event_list.mount(EventListItem(ev))

    def on_event_list_item_selected(self, message: EventListItem.Selected) -> None:
        # Clear previous selection highlight
        for item in self.query(EventListItem):
            item.remove_class("selected")
            if item._uid == message.uid:
                item.add_class("selected")
        self._selected_uid = message.uid

    def watch__selected_uid(self, uid: int | None) -> None:
        if uid is None:
            return
        self._update_detail(uid)

    def _update_detail(self, uid: int) -> None:
        ev = db.get_event(uid)
        detail = self.query_one("#logi-detail", Static)
        table  = self.query_one("#logi-companies", DataTable)
        table.clear()

        if not ev:
            detail.update("Event not found.")
            return

        color    = _SEVERITY_COLOR.get(ev.get("severity") or "", "white")
        severity = ev.get("severity") or "—"
        text = Text()
        text.append(f"{ev.get('title') or ''}\n", style="bold")
        text.append(f"Region: {ev.get('region') or '—'}   ", style="dim")
        text.append(f"Type: {ev.get('event_type') or '—'}   ", style="dim")
        text.append(f"Severity: ", style="dim")
        text.append(severity, style=f"bold {color}")
        text.append(f"   Date: {(ev.get('event_date') or '')[:10]}\n", style="dim")

        # Parse affected/beneficiary sector JSON if present
        try:
            import json as _json
            aff = _json.loads(ev.get("affected_sectors") or "[]")
            ben = _json.loads(ev.get("beneficiary_sectors") or "[]")
        except Exception:
            aff, ben = [], []
        if aff:
            text.append(f"Affected:    {', '.join(aff[:4])}\n", style="dim")
        if ben:
            text.append(f"Beneficiary: {', '.join(ben[:4])}", style="green dim")
        detail.update(text)

        stocks = db.get_event_stocks(uid)
        if not stocks:
            table.add_row("—", "No linked companies yet", "", "", "", "")
            return
        for s in stocks:
            role_color = "red" if s.get("role") == "impacted" else "green"
            role_cell  = Text(s.get("role") or "", style=role_color)
            table.add_row(
                role_cell,
                s.get("ticker") or "—",
                (s.get("sector") or "—")[:22],
                (s.get("cannot_provide") or "—")[:28],
                (s.get("will_redirect") or "—")[:28],
                s.get("confidence") or "—",
            )


# ── Settings panel ────────────────────────────────────────────────────────────

class SettingsPanel(Vertical):
    CSS = """
    SettingsPanel { padding: 2 3; height: 1fr; overflow-y: auto; }
    .panel-title  { text-style: bold; color: $primary; margin-bottom: 1; }
    .section-title { text-style: bold; color: $accent; margin-top: 2; margin-bottom: 0; }
    .setting-label { color: $text-muted; margin-bottom: 0; margin-top: 1; }
    .setting-input { margin-bottom: 0; }
    .setting-note  { color: $text-muted; margin-bottom: 1; text-style: italic; }
    #settings-status { margin-top: 1; height: 1; }
    #save-btn { width: 22; margin-top: 2; }
    """

    _FEED_FIELDS: list[tuple[str, str]] = [
        ("wsj_podcast_feed_1",  "WSJ — The Journal"),
        ("wsj_podcast_feed_2",  "WSJ — What's News"),
        ("morgan_stanley_feed", "Morgan Stanley — Thoughts on the Market"),
        ("motley_fool_feed",    "Motley Fool Money"),
        ("whisper_model",       "Whisper Model  (base / small / medium / large)"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("SETTINGS", classes="panel-title")
        yield Label("News Sources — Podcast RSS Feeds", classes="section-title")
        yield Label(
            "Verify URLs via Apple Podcasts → share → copy RSS link before first run.",
            classes="setting-note",
        )
        for key, label in self._FEED_FIELDS:
            yield Label(label, classes="setting-label")
            yield Input(placeholder="RSS feed URL or model name", id=f"set-{key}", classes="setting-input")
        yield Button("Save Settings", variant="primary", id="save-btn")
        yield Label("", id="settings-status")

    def on_mount(self) -> None:
        user     = getattr(self.app, "current_user", {})
        user_uid = user.get("user_uid", 1)
        saved    = db.get_all_settings(user_uid)

        _wsj_urls = [u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_WSJ_PODCAST]
        defaults: dict[str, str] = {
            "wsj_podcast_feed_1":  _wsj_urls[0] if len(_wsj_urls) > 0 else "",
            "wsj_podcast_feed_2":  _wsj_urls[1] if len(_wsj_urls) > 1 else "",
            "morgan_stanley_feed": next((u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MORGAN_STANLEY), ""),
            "motley_fool_feed":    next((u for s, u in PODCAST_FEEDS if s == NEWS_SOURCE_MOTLEY_FOOL), ""),
            "whisper_model":       NEWS_WHISPER_MODEL,
        }
        for key, _ in self._FEED_FIELDS:
            self.query_one(f"#set-{key}", Input).value = saved.get(key) or defaults.get(key, "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()

    def _save(self) -> None:
        user     = getattr(self.app, "current_user", {})
        user_uid = user.get("user_uid", 1)
        for key, _ in self._FEED_FIELDS:
            val = self.query_one(f"#set-{key}", Input).value.strip()
            db.set_setting(user_uid, key, val)
        self.query_one("#settings-status", Label).update(
            "[green]Settings saved.[/green]"
        )


# ── Main screen ────────────────────────────────────────────────────────────────

class MainScreen(Screen):
    BINDINGS = [
        Binding("1", "section('home')",      "Home"),
        Binding("2", "section('research')",  "Research"),
        Binding("3", "section('logistics')", "Logistics"),
        Binding("4", "section('settings')",  "Settings"),
        Binding("q", "quit_app",             "Quit"),
    ]
    CSS = """
    MainScreen { layout: horizontal; }
    #content { width: 1fr; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Sidebar(id="sidebar"),
            Container(
                HomePanel(id="panel-home"),
                ResearchPanel(id="panel-research"),
                LogisticsPanel(id="panel-logistics"),
                SettingsPanel(id="panel-settings"),
                id="content",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._show_section("home")
        self.title = "StackScreener"
        user = getattr(self.app, "current_user", {})
        self.sub_title = user.get("display_name") or user.get("username") or ""

    def action_section(self, section: str) -> None:
        self._show_section(section)

    def action_quit_app(self) -> None:
        self.app.exit()

    def _show_section(self, section: str) -> None:
        for name in ("home", "research", "logistics", "settings"):
            self.query_one(f"#panel-{name}").display = (name == section)
        self.query_one(Sidebar).set_active(section)

    def switch_section(self, section: str) -> None:
        self._show_section(section)


# ── App ────────────────────────────────────────────────────────────────────────

class StackScreenerApp(App):
    TITLE = "StackScreener"
    CSS_PATH = None
    current_user: dict = {}

    def on_mount(self) -> None:
        db.init_db()
        self.push_screen(LoginScreen())

    def switch_section(self, section: str) -> None:
        try:
            self.query_one(MainScreen).switch_section(section)
        except Exception:
            pass


def main() -> None:
    StackScreenerApp().run()


if __name__ == "__main__":
    main()
