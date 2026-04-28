"""
tui/tabs.py — Research sub-tabs: Screener, Calendar, StockComparison, StockPicks,
              ResearchReports, News.
"""
from __future__ import annotations

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button, Collapsible, DataTable, Input, Label, Select, Static,
    TabbedContent, TabPane,
)

import db
from screener_config import (
    CALENDAR_EVENT_STYLES,
    NEWS_SOURCE_CNBC,
    NEWS_SOURCE_LLOYDS_LIST,
    NEWS_SOURCE_MORGAN_STANLEY,
    NEWS_SOURCE_MOTLEY_FOOL,
    NEWS_SOURCE_RIO_TIMES,
    NEWS_SOURCE_WSJ_PDF,
    NEWS_SOURCE_WSJ_PODCAST,
    NEWS_SOURCE_YAHOO_FINANCE,
    SCREENER_MCAP_BUCKETS,
    SCREENER_PE_BUCKETS,
    SIGNAL_SOURCE_LABELS,
)
from .formatters import _fmt_mcap, _fmt_pct, _fmt_ratio, _score_bar, _week_dates
from .modals import StockQuoteModal


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
                while len(vals) < 4:
                    vals.append(None)
                fmt_vals = [_fmt_cmp_val(field, v) for v in vals[:len(tickers)]]

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
    ("Lloyd's List",  NEWS_SOURCE_LLOYDS_LIST),
    ("Rio Times",     NEWS_SOURCE_RIO_TIMES),
]

_NEWS_SOURCE_DISPLAY: dict[str, str] = {
    NEWS_SOURCE_WSJ_PODCAST:    "WSJ Podcast",
    NEWS_SOURCE_WSJ_PDF:        "WSJ PDF",
    NEWS_SOURCE_MORGAN_STANLEY: "Morgan Stanley",
    NEWS_SOURCE_MOTLEY_FOOL:    "Motley Fool",
    NEWS_SOURCE_YAHOO_FINANCE:  "Yahoo Finance",
    NEWS_SOURCE_LLOYDS_LIST:    "Lloyd's List",
    NEWS_SOURCE_RIO_TIMES:      "Rio Times",
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
