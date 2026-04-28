"""
tui/panels.py — Sidebar, content panels (Home, Research, Logistics, Settings),
                and MainScreen.
"""
from __future__ import annotations

import json as _json

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, Static,
    TabbedContent, TabPane,
)

import db
from screener_config import (
    HEATMAP_COLORS, HEATMAP_DEFAULT_LIMIT, HEATMAP_FILTERS,
    HEATMAP_LARGE_CAP_THRESHOLD, HEATMAP_MEGA_CAP_THRESHOLD, HEATMAP_SP500_LIMIT,
    NEWS_SOURCE_MORGAN_STANLEY, NEWS_SOURCE_MOTLEY_FOOL,
    NEWS_SOURCE_WSJ_PODCAST,
    NEWS_WHISPER_MODEL,
    PODCAST_FEEDS,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_LOW, SEVERITY_MEDIUM,
)
from .formatters import _fmt_mcap
from .modals import StockQuoteModal
from .tabs import (
    CalendarTab, NewsTab, ResearchReportsTab,
    ScreenerTab, StockComparisonTab, StockPicksTab,
)

_SEVERITY_COLOR: dict[str, str] = {
    SEVERITY_CRITICAL: "red",
    SEVERITY_HIGH:     "dark_orange",
    SEVERITY_MEDIUM:   "yellow",
    SEVERITY_LOW:      "blue",
}

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


# ── Heatmap ────────────────────────────────────────────────────────────────────

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

    fill(3,  9,  1, 2)
    fill(7,  22, 2, 7)
    fill(12, 17, 6, 8)
    fill(14, 18, 7, 8)
    fill(15, 23, 8, 13)
    fill(16, 19, 13, 14)
    fill(22, 30, 0, 2)
    fill(33, 36, 2, 4)
    fill(35, 43, 1, 2)
    fill(36, 44, 2, 5)
    fill(32, 47, 5, 10)
    fill(38, 51, 4, 5)
    fill(40, 51, 5, 9)
    fill(40, 50, 9, 14)
    fill(51, 53, 10, 12)
    fill(42, 74, 0, 4)
    fill(44, 66, 4, 5)
    fill(50, 57, 5, 9)
    fill(52, 68, 3, 7)
    fill(64, 72, 3, 6)
    fill(57, 68, 7, 11)
    fill(61, 68, 9, 11)
    fill(60, 66, 10, 11)
    fill(60, 71, 10, 15)
    fill(70, 73, 13, 15)

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
        limit          = HEATMAP_DEFAULT_LIMIT
        min_mcap       = None
        watchlist_only = False
        match mode:
            case "Large Cap": min_mcap = HEATMAP_LARGE_CAP_THRESHOLD
            case "Mega Cap":  min_mcap = HEATMAP_MEGA_CAP_THRESHOLD
            case "S&P ≈500":  limit    = HEATMAP_SP500_LIMIT
            case "Watchlist": watchlist_only = True

        stocks = db.get_heatmap_stocks(limit=limit, min_mcap=min_mcap, watchlist_only=watchlist_only)
        grid   = self.query_one("#heatmap-grid", Container)
        grid.remove_children()

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


# ── Logistics panel ────────────────────────────────────────────────────────────

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

        try:
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
