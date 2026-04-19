"""
app.py — StackScreener desktop TUI (Textual).

Entry point for the interactive terminal application.
Phase 1a: login, sidebar navigation, stub content panels.

Usage:
    python app.py
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    Static, TabbedContent, TabPane,
)

import db
from screener_config import DEBUG_MODE

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
    .login-input {
        margin-bottom: 1;
    }
    #login-btn {
        width: 100%;
        margin-top: 1;
    }
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
    #change-error {
        color: $error;
        text-align: center;
        height: 1;
        margin-top: 1;
    }
    .change-input {
        margin-bottom: 1;
    }
    #change-btn {
        width: 100%;
        margin-top: 1;
    }
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
    """Clickable sidebar navigation item."""

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
    NavItem {
        padding: 1 2;
        color: $text-muted;
    }
    NavItem:hover {
        background: $primary-darken-2;
        color: $text;
    }
    NavItem.active {
        background: $primary;
        color: $background;
        text-style: bold;
    }
    #sidebar-user {
        dock: bottom;
        padding: 1 2;
        color: $text-muted;
        border-top: solid $primary-darken-3;
        text-overflow: ellipsis;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("STACKSCREENER", id="sidebar-title")
        yield NavItem("  HOME",      "home",      id="nav-home")
        yield NavItem("  RESEARCH",  "research",  id="nav-research")
        yield NavItem("  LOGISTICS", "logistics", id="nav-logistics")
        user = getattr(self.app, "current_user", None)
        name = user.get("display_name") or user.get("username") if user else ""
        yield Label(f"  {name}", id="sidebar-user")

    def set_active(self, section: str) -> None:
        for item in self.query(NavItem):
            item.remove_class("active")
        nav = self.query_one(f"#nav-{section}", NavItem)
        nav.add_class("active")


# ── Content panels ─────────────────────────────────────────────────────────────

class HomePanel(ScrollableContainer):
    CSS = """
    HomePanel {
        padding: 2;
    }
    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    .stat-row {
        margin-bottom: 1;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("HOME — Market Overview", classes="panel-title")
        yield Label("Loading...", id="home-stats")

    def on_mount(self) -> None:
        self._load_stats()

    def _load_stats(self) -> None:
        try:
            scans = db.get_recent_scans(1)
            events = db.get_active_events()
            total = db.query_one("SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0")
            enriched = db.query_one(
                "SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0 AND last_enriched_at IS NOT NULL"
            )
            last_scan = scans[0] if scans else None
            lines = [
                f"Active stocks:   {total['n'] if total else '?'}",
                f"Enriched:        {enriched['n'] if enriched else '?'}",
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
                lines.append("\nNo scans run yet. Use: python screener_run.py")
            self.query_one("#home-stats", Label).update("\n".join(lines))
        except Exception as e:
            self.query_one("#home-stats", Label).update(f"Error loading stats: {e}")


class ResearchPanel(ScrollableContainer):
    CSS = """
    ResearchPanel {
        padding: 1;
    }
    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("RESEARCH", classes="panel-title")
        with TabbedContent(
            "Screener", "Calendar", "Stock Comparison", "Stock Picks", "Research Reports"
        ):
            with TabPane("Screener"):
                yield ScreenerTab()
            with TabPane("Calendar"):
                yield Label("Calendar — coming in Phase 1c")
            with TabPane("Stock Comparison"):
                yield Label("Stock Comparison — coming in Phase 1c")
            with TabPane("Stock Picks"):
                yield Label("Stock Picks — coming in Phase 1c")
            with TabPane("Research Reports"):
                yield Label("Research Reports — coming in Phase 1c")


class ScreenerTab(ScrollableContainer):
    CSS = """
    ScreenerTab {
        height: 1fr;
        padding: 1;
    }
    #screener-table {
        height: 1fr;
    }
    #screener-note {
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="screener-note")
        yield DataTable(id="screener-table")

    def on_mount(self) -> None:
        self._load_results()

    def _load_results(self) -> None:
        scans = db.get_recent_scans(1)
        table = self.query_one(DataTable)
        table.add_columns("Rank", "Ticker", "Exchange", "Sector", "Score", "Price", "SC", "Flow")
        if not scans:
            self.query_one("#screener-note", Label).update(
                "No scan results yet. Run: python screener_run.py"
            )
            return
        scan = scans[0]
        results = db.get_scan_results(scan["scan_uid"], limit=100)
        self.query_one("#screener-note", Label).update(
            f"Scan #{scan['scan_uid']}  mode={scan['scan_mode']}  "
            f"scored={scan.get('scored_count') or 0}  "
            f"at {(scan.get('started_at') or '')[:19]}"
        )
        for r in results:
            table.add_row(
                str(r["composite_rank"]),
                r["ticker"],
                r["exchange"],
                r.get("sector") or "",
                f"{r['composite_score']:.1f}",
                f"{(r.get('price_at_scan') or 0):.2f}",
                f"{(r.get('score_supply_chain') or 0):.0f}",
                f"{(r.get('score_inst_flow') or 0):.0f}",
            )


class LogisticsPanel(ScrollableContainer):
    CSS = """
    LogisticsPanel {
        padding: 2;
    }
    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #logistics-table {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("LOGISTICS — Active Supply Chain Events", classes="panel-title")
        yield DataTable(id="logistics-table")

    def on_mount(self) -> None:
        self._load_events()

    def _load_events(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Region", "Title", "Type", "Severity", "Event Date")
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


# ── Main screen ────────────────────────────────────────────────────────────────

class MainScreen(Screen):
    BINDINGS = [
        Binding("1", "section('home')",      "Home",      show=True),
        Binding("2", "section('research')",  "Research",  show=True),
        Binding("3", "section('logistics')", "Logistics", show=True),
        Binding("q", "quit_app",             "Quit",      show=True),
    ]

    CSS = """
    MainScreen {
        layout: horizontal;
    }
    #content {
        width: 1fr;
        height: 100%;
    }
    """

    _active_section: str = "home"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            Sidebar(id="sidebar"),
            Container(
                HomePanel(id="panel-home"),
                ResearchPanel(id="panel-research"),
                LogisticsPanel(id="panel-logistics"),
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
        self._active_section = section
        for name in ("home", "research", "logistics"):
            panel = self.query_one(f"#panel-{name}")
            panel.display = (name == section)
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
