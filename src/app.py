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

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button, Collapsible, DataTable, Footer, Header,
    Input, Label, Select, Static, TabbedContent, TabPane,
)

import db
from screener_config import (
    DEBUG_MODE,
    NEWS_WHISPER_MODEL,
    WSJ_PODCAST_FEEDS,
    MORGAN_STANLEY_PODCAST_FEED,
    MOTLEY_FOOL_PODCAST_FEED,
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
        user = getattr(self.app, "current_user", None)
        name = (user.get("display_name") or user.get("username")) if user else ""
        yield Label(f"  {name}", id="sidebar-user")

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

_MCAP_BUCKETS = {
    "Mega (>200B)": 200e9,
    "Large (10B+)": 10e9,
    "Mid (2B+)":    2e9,
    "Small (<2B)":  0.0,
}

_PE_BUCKETS = {
    "<15":    (0,    15),
    "15–25":  (15,   25),
    "25–50":  (25,   50),
    ">50":    (50, 9999),
}

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
                [("MCap: Any", ""), *[(k, k) for k in _MCAP_BUCKETS]],
                value="", id="scr-mcap", allow_blank=False,
            )
            yield Select(
                [("P/E: Any", ""), *[(k, k) for k in _PE_BUCKETS]],
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
        self._all_results = db.get_scan_results(scan["scan_uid"])
        # populate sector filter dynamically
        sectors = sorted({r.get("sector") or "" for r in self._all_results if r.get("sector")})
        sel = self.query_one("#scr-sector", Select)
        sel.set_options([("Sector: Any", ""), *[(s, s) for s in sectors]])
        self.query_one("#scr-note", Label).update(
            f"Scan #{scan['scan_uid']}  mode={scan['scan_mode']}  "
            f"scored={scan.get('scored_count') or 0}  "
            f"at {(scan.get('started_at') or '')[:19]}"
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

        mcap_min = _MCAP_BUCKETS.get(mcap_key, 0) if mcap_key else 0
        mcap_max = (
            _MCAP_BUCKETS.get(list(_MCAP_BUCKETS.keys())[
                list(_MCAP_BUCKETS.keys()).index(mcap_key) - 1
            ], 9e18) if mcap_key and list(_MCAP_BUCKETS.keys()).index(mcap_key) > 0 else 9e18
        ) if mcap_key else 9e18
        pe_range = _PE_BUCKETS.get(pe_key) if pe_key else None
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
            )


# ── Calendar tab ───────────────────────────────────────────────────────────────

_EVENT_STYLE: dict[str, str] = {
    "earnings": "green",
    "split":    "cyan",
    "ipo":      "yellow",
    "economic": "magenta",
}

_FILTER_TO_ETYPE: dict[str, str | None] = {
    "all":      None,
    "earnings": "earnings",
    "splits":   "split",
    "ipos":     "ipo",
    "economic": "economic",
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
            style = _EVENT_STYLE.get(etype, "white")
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
            for lbl, key in [("All", "all"), ("Earnings", "earnings"),
                              ("Splits", "splits"), ("IPOs", "ipos"), ("Economic", "economic")]:
                yield Button(lbl, id=f"cal-f-{key}", classes="cal-filter")
        with Horizontal(id="week-grid"):
            for i in range(7):
                yield DayCell(id=f"day-{i}")
        yield DataTable(id="cal-detail", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Ticker", "Event", "Date", "Details")
        self.query_one("#cal-f-all", Button).add_class("active")
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

        stocks = [db.get_stock_by_ticker(t) for t in tickers]
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

_SOURCE_LABELS: dict[str, str] = {
    "senate_watcher": "Senate Watcher",
    "house_watcher":  "House Watcher",
    "sec_form4":      "SEC Form 4",
    "sec_13f":        "SEC 13F",
    "yahoo_finance":  "Yahoo Finance",
    "options_flow":   "Options Flow",
}


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
            self.mount(card)

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
                src  = _SOURCE_LABELS.get(sig.get("source") or "", sig.get("source") or "")
                sub  = sig.get("sub_score")
                sub_str = f"{sub:.0f}" if sub is not None else "—"
                reason = (sig.get("reason_text") or "")[:60]
                lines.append(f"    [{src:<18}] {sub_str:>4}  {reason}")
        else:
            lines.append("  No source signals yet — will populate in Phase 3 (inst flow).")
        return Static("\n".join(lines), classes="pick-detail")


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

class HomePanel(ScrollableContainer):
    CSS = """
    HomePanel { padding: 2; }
    .panel-title { text-style: bold; color: $primary; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Label("HOME — Market Overview", classes="panel-title")
        yield Label("Loading...", id="home-stats")

    def on_mount(self) -> None:
        self._load_stats()

    def _load_stats(self) -> None:
        try:
            scans    = db.get_recent_scans(1)
            events   = db.get_active_events()
            total    = db.query_one("SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0")
            enriched = db.query_one(
                "SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0 AND last_enriched_at IS NOT NULL"
            )
            last_scan = scans[0] if scans else None
            lines = [
                f"Active stocks:    {total['n'] if total else '?'}",
                f"Enriched:         {enriched['n'] if enriched else '?'}",
                f"Active SC events: {len(events)}",
            ]
            if last_scan:
                lines += [
                    "",
                    f"Last scan:  #{last_scan['scan_uid']}  mode={last_scan['scan_mode']}",
                    f"  Scored:   {last_scan.get('scored_count') or 0}",
                    f"  Status:   {last_scan['status']}",
                    f"  At:       {(last_scan.get('started_at') or '')[:19]}",
                ]
            else:
                lines.append("\nNo scans run yet.  Run: python screener_run.py")
            self.query_one("#home-stats", Label).update("\n".join(lines))
        except Exception as e:
            self.query_one("#home-stats", Label).update(f"Error: {e}")


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


class LogisticsPanel(ScrollableContainer):
    CSS = """
    LogisticsPanel { padding: 2; }
    .panel-title { text-style: bold; color: $primary; margin-bottom: 1; }
    #logistics-table { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield Label("LOGISTICS — Active Supply Chain Events", classes="panel-title")
        yield DataTable(id="logistics-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Region", "Title", "Type", "Severity", "Date")
        events = db.get_active_events()
        if not events:
            table.add_row("—", "No active events", "", "", "", "")
            return
        for ev in events:
            table.add_row(
                str(ev["supply_chain_event_uid"]),
                ev.get("region") or "",
                ev.get("title") or "",
                ev.get("event_type") or "",
                ev.get("severity") or "",
                (ev.get("event_date") or "")[:10],
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

        defaults: dict[str, str] = {
            "wsj_podcast_feed_1":  WSJ_PODCAST_FEEDS[0] if WSJ_PODCAST_FEEDS else "",
            "wsj_podcast_feed_2":  WSJ_PODCAST_FEEDS[1] if len(WSJ_PODCAST_FEEDS) > 1 else "",
            "morgan_stanley_feed": MORGAN_STANLEY_PODCAST_FEED,
            "motley_fool_feed":    MOTLEY_FOOL_PODCAST_FEED,
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
