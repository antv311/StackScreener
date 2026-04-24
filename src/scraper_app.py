"""
scraper_app.py — P1 Data Scraper TUI for StackScreener.

Provides a terminal UI for triggering data pipeline commands, monitoring the
LLM job queue, tailing live subprocess output, and managing API source keys.

Usage:
    python src/scraper_app.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    RichLog, Select, Static, TabbedContent, TabPane, TextArea,
)
from textual.screen import ModalScreen

import json as _json

import db
from screener_config import DEBUG_MODE, KNOWN_API_ROLES, CONNECTOR_TEMPLATES, ROLE_NEWS_CONNECTOR
import news as _news_module

def _btn_id(label: str) -> str:
    """Convert a button label to a valid Textual CSS identifier."""
    return "btn-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def _job_description(job: dict) -> str:
    """Human-readable one-liner from a job's input_json."""
    try:
        data = _json.loads(job.get("input_json") or "{}")
    except Exception:
        return str(job.get("source_ref") or "")
    match job.get("job_type"):
        case "classify_news":
            text = data.get("headline") or data.get("body") or str(job.get("source_ref") or "")
            return text[:70] + ("…" if len(text) > 70 else "")
        case "extract_10k" | "parse_8k":
            return data.get("ticker") or str(job.get("source_ref") or "")
        case _:
            return str(job.get("source_ref") or "")


# ── Pipeline command definitions ───────────────────────────────────────────────

_SRC = str(Path(__file__).parent)

_COMMANDS: list[tuple[str, str, list[str]]] = [
    # (button label, description, argv relative to venv python)
    ("Seed Stock Universe",    "seeder.py",                 [sys.executable, f"{_SRC}/seeder.py"]),
    ("Enrich Fundamentals",   "enricher.py",                    [sys.executable, f"{_SRC}/enricher.py"]),
    ("Force Re-enrich All",   "enricher.py --force",            [sys.executable, f"{_SRC}/enricher.py", "--force"]),
    ("Fetch Price History",   "enricher.py --history-only",     [sys.executable, f"{_SRC}/enricher.py", "--history-only"]),
    ("EDGAR CIKs",            "edgar.py --seed-ciks",      [sys.executable, f"{_SRC}/edgar.py", "--seed-ciks"]),
    ("EDGAR XBRL Facts",      "edgar.py --fetch-facts",    [sys.executable, f"{_SRC}/edgar.py", "--fetch-facts", "--limit", "100"]),
    ("10-K Fetch & Cache",    "edgar.py --fetch-filings",      [sys.executable, f"{_SRC}/edgar.py", "--fetch-filings"]),
    ("10-K Check New",        "edgar.py --check-new-filings", [sys.executable, f"{_SRC}/edgar.py", "--check-new-filings"]),
    ("EDGAR 8-K Events",      "edgar.py --fetch-8k",          [sys.executable, f"{_SRC}/edgar.py", "--fetch-8k", "--limit", "100"]),
    ("Form 4 Insider Trades", "inst_flow.py --form4",      [sys.executable, f"{_SRC}/inst_flow.py", "--form4"]),
    ("Form 13F Holdings",     "inst_flow.py --form13f",    [sys.executable, f"{_SRC}/inst_flow.py", "--form13f"]),
    ("Options Flow",          "inst_flow.py --options",    [sys.executable, f"{_SRC}/inst_flow.py", "--options"]),
    ("News — All Sources",    "news.py --all",             [sys.executable, f"{_SRC}/news.py", "--all"]),
    ("News — All Connectors", "news.py --connectors",      [sys.executable, f"{_SRC}/news.py", "--newsapi-all", "--connectors"]),
    ("News — Classify",       "news.py --classify",        [sys.executable, f"{_SRC}/news.py", "--classify"]),
    ("USDA Crop Conditions",  "commodities.py --usda",     [sys.executable, f"{_SRC}/commodities.py", "--usda-crops"]),
    ("EIA Petroleum",         "commodities.py --eia",      [sys.executable, f"{_SRC}/commodities.py", "--eia-petroleum"]),
    ("AIS Chokepoints",       "logistics.py --choke",      [sys.executable, f"{_SRC}/logistics.py", "--chokepoints"]),
    ("Panama Canal",          "logistics.py --panama",     [sys.executable, f"{_SRC}/logistics.py", "--panama"]),
    ("Supply Chain Seed",     "supply_chain.py --seed",    [sys.executable, f"{_SRC}/supply_chain.py", "--seed-tier2"]),
]


# ── Unified Endpoint Modal ─────────────────────────────────────────────────────

class EndpointModal(ModalScreen):
    """Add or edit an API endpoint — key + connector config in one modal (3-click rule).

    Add mode  (name=""): role Select + label + key; connector section shown for news_connector.
    Edit mode (name set): display name + key; connector section shown when role=news_connector.
    """

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(
        self,
        name: str = "",
        current_key: str = "",
        current_display: str = "",
        current_url: str = "",
        current_config: str = "",
        current_role: str = "",
    ) -> None:
        super().__init__()
        self._name            = name
        self._current_key     = current_key
        self._current_display = current_display
        self._current_url     = current_url
        self._current_config  = current_config or "{}"
        self._current_role    = current_role
        self._is_new          = name == ""

    def compose(self) -> ComposeResult:
        title = "Add Endpoint" if self._is_new else f"Edit Endpoint — {self._name}"
        template_options = [(n, n) for n in CONNECTOR_TEMPLATES]
        with Vertical(id="modal-box"):
            yield Static(title, id="modal-title")
            if self._is_new:
                options = [(desc, role) for role, desc in KNOWN_API_ROLES]
                yield Static("Role", classes="modal-label")
                yield Select(options, id="role-select", prompt="Select a data source role...")
                yield Static("Label (required for News Connectors)", classes="modal-label")
                yield Input(placeholder="e.g. TheNewsAPI, Finnhub, Bloomberg Feed", id="label-input")
            else:
                yield Static("Display name (optional)", classes="modal-label")
                yield Input(value=self._current_display, placeholder="e.g. Bloomberg Shipping", id="display-input")
            yield Static("API Key", classes="modal-label")
            yield Input(value=self._current_key, placeholder="Paste key here...", id="key-input", password=True)
            # Connector section — hidden until news_connector role is active
            with Vertical(id="connector-section"):
                yield Static("Endpoint URL", classes="modal-label")
                yield Input(value=self._current_url, placeholder="https://api.example.com/v1/news", id="url-input")
                yield Static("Template (pre-fills config below)", classes="modal-label")
                yield Select(template_options, id="template-select", prompt="Choose a template to pre-fill...")
                yield Static("Connector Config (JSON)", classes="modal-label")
                yield TextArea(self._current_config, id="config-textarea", language="json")
                yield Static("", id="test-result")
            with Horizontal(id="modal-buttons"):
                yield Button("Save",            variant="primary", id="save-btn")
                yield Button("Test Connection", variant="default", id="test-btn")
                yield Button("Cancel",          variant="default", id="cancel-btn")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "template-select" and event.value is not Select.BLANK:
            tpl = CONNECTOR_TEMPLATES.get(str(event.value), {})
            self.query_one("#config-textarea", TextArea).load_text(
                _json.dumps(tpl, indent=2)
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "save-btn":
                self._save()
            case "test-btn":
                self._test()
            case "cancel-btn":
                self.dismiss(None)

    # ── private save/test helpers ──────────────────────────────────────────────

    def _save(self) -> None:
        if self._is_new:
            sel = self.query_one("#role-select", Select)
            if sel.value is Select.BLANK:
                return
            role  = str(sel.value)
            label = self.query_one("#label-input", Input).value.strip()
            name  = label if (role == ROLE_NEWS_CONNECTOR and label) else role
            new_key = self.query_one("#key-input", Input).value.strip()
            if not name or not new_key:
                return
            db.set_api_key(1, name, new_key, display_name=label or None, role=role)
            if not self._write_connector(name):
                return
        else:
            name = self._name
            new_key      = self.query_one("#key-input", Input).value.strip()
            display_name = self.query_one("#display-input", Input).value.strip() or None
            if new_key:
                db.set_api_key(1, name, new_key, display_name=display_name)
            elif display_name is not None:
                db.execute(
                    "UPDATE api_keys SET display_name = ? WHERE user_uid = 1 AND name = ?",
                    (display_name, name),
                )
            if not self._write_connector(name):
                return
        self.dismiss("saved")

    def _write_connector(self, name: str) -> bool:
        """Persist URL + connector config. Skip silently when both are empty (system keys)."""
        url        = self.query_one("#url-input", Input).value.strip()
        config_raw = self.query_one("#config-textarea", TextArea).text.strip()
        if not url and (not config_raw or config_raw == "{}"):
            return True  # nothing to save — system key with no endpoint config
        try:
            _json.loads(config_raw)
        except Exception:
            self.query_one("#test-result", Static).update(
                "[red]Invalid JSON — fix config before saving.[/]"
            )
            return False
        db.execute(
            "UPDATE api_keys SET url = ?, connector_config = ?, "
            "role = COALESCE(role, ?) WHERE user_uid = 1 AND name = ?",
            (url, config_raw, ROLE_NEWS_CONNECTOR, name),
        )
        return True

    def _test(self) -> None:
        if self._is_new:
            name = self.query_one("#label-input", Input).value.strip()
            if not name:
                self.query_one("#test-result", Static).update("[red]Enter a label first.[/]")
                return
        else:
            name = self._name
        url        = self.query_one("#url-input", Input).value.strip()
        config_raw = self.query_one("#config-textarea", TextArea).text.strip()
        if url:
            db.execute("UPDATE api_keys SET url = ? WHERE user_uid = 1 AND name = ?", (url, name))
        try:
            _json.loads(config_raw)
            db.set_connector_config(1, name, config_raw)
        except Exception:
            self.query_one("#test-result", Static).update("[red]Invalid JSON — fix config before testing.[/]")
            return
        self.query_one("#test-result", Static).update("[dim]Testing...[/]")
        ok, msg = _news_module.test_news_connector(name)
        colour = "green" if ok else "red"
        self.query_one("#test-result", Static).update(f"[{colour}]{msg}[/{colour}]")

    DEFAULT_CSS = """
    EndpointModal {
        align: center middle;
    }
    #modal-box {
        width: 80;
        height: auto;
        max-height: 42;
        padding: 2 3;
        background: $surface;
        border: thick $primary;
    }
    #modal-title {
        text-align: center;
        color: $accent;
        margin-bottom: 1;
    }
    .modal-label {
        color: $text-muted;
        margin-top: 1;
    }
    #connector-section {
        border-top: solid $primary-darken-3;
        margin-top: 1;
        padding-top: 1;
    }
    #config-textarea {
        height: 10;
        margin-top: 1;
    }
    #test-result {
        height: 1;
        margin-top: 1;
    }
    #modal-buttons {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    """


# ── Main TUI ───────────────────────────────────────────────────────────────────

class ScraperApp(App):
    """P1 Data Scraper TUI — pipeline triggers, LLM queue, log tail, source manager."""

    TITLE   = "StackScreener — Data Scraper"
    CSS_PATH = None

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    Screen {
        layout: horizontal;
    }
    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary-darken-2;
        padding: 1 0;
        overflow-y: auto;
    }
    #sidebar-title {
        text-align: center;
        color: $accent;
        padding: 0 1 1 1;
        border-bottom: solid $primary-darken-3;
        margin-bottom: 1;
    }
    .pipeline-btn {
        width: 100%;
        margin: 0 1 1 1;
        height: 3;
    }
    #worker-section {
        margin-top: 1;
        border-top: solid $primary-darken-3;
        padding-top: 1;
    }
    #worker-label {
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    #worker-btn {
        width: 100%;
        margin: 0 1;
    }
    #worker-limit-input {
        width: 100%;
        margin: 0 1 1 1;
    }
    #queue-controls {
        height: auto;
        margin-bottom: 1;
        align: left middle;
    }
    #queue-type-select {
        width: 22;
    }
    #priority-input {
        width: 10;
    }
    #queue-progress {
        height: auto;
        margin: 0 0 1 0;
        color: $text-muted;
    }
    #sources-btn-row {
        height: auto;
        margin-bottom: 1;
    }
    #add-key-btn {
        width: auto;
    }
    #news-tab-content {
        height: 1fr;
        layout: vertical;
    }
    #news-sources-header {
        height: auto;
        padding: 0 0 1 0;
    }
    #source-filter {
        width: 1fr;
        margin-left: 1;
    }
    #news-sources-table {
        height: 1fr;
        min-height: 10;
    }
    #news-keywords-section {
        height: auto;
        max-height: 14;
        border-top: solid $primary-darken-3;
        padding-top: 1;
        margin-top: 1;
    }
    #keywords-header {
        color: $accent;
        margin-bottom: 1;
    }
    #keyword-input-row {
        height: auto;
        margin-bottom: 1;
    }
    #keyword-input {
        width: 1fr;
    }
    #add-keyword-btn {
        width: auto;
        margin-left: 1;
    }
    #keywords-table {
        height: 6;
    }
    #main-area {
        width: 1fr;
    }
    #stats-bar {
        height: 1;
        background: $primary-darken-2;
        padding: 0 2;
        color: $text;
    }
    RichLog {
        height: 1fr;
        border: none;
    }
    DataTable {
        height: 1fr;
    }
    TabPane {
        padding: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._worker_proc: asyncio.subprocess.Process | None = None
        self._active_proc: asyncio.subprocess.Process | None = None
        self._all_sources: list[dict] = []
        self._queue_sort_col: str = "job_uid"
        self._queue_sort_asc: bool  = True

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("Pipeline Commands", id="sidebar-title")
                for label, _desc, _argv in _COMMANDS:
                    yield Button(label, classes="pipeline-btn", id=_btn_id(label))
                with Vertical(id="worker-section"):
                    yield Static("LLM Worker", id="worker-label")
                    yield Button("Start Worker", id="worker-btn", variant="success")
                    yield Input(placeholder="Limit (jobs)", id="worker-limit-input")
            with Vertical(id="main-area"):
                yield Label("", id="stats-bar")
                with TabbedContent():
                    with TabPane("Logs", id="tab-logs"):
                        yield RichLog(id="log", highlight=True, markup=True)
                    with TabPane("Queue", id="tab-queue"):
                        with Horizontal(id="queue-controls"):
                            yield Select(
                                [("All Types", "")],
                                id="queue-type-select",
                                value="",
                                allow_blank=False,
                            )
                            yield Button("⏸ Pause",  id="pause-jobs-btn",  variant="warning")
                            yield Button("▶ Resume", id="resume-jobs-btn", variant="success")
                            yield Button("✕ Cancel", id="cancel-jobs-btn", variant="error")
                            yield Input("5", placeholder="Priority 1-9", id="priority-input", restrict=r"[1-9]")
                            yield Button("Set Priority", id="set-priority-btn")
                        yield Static("", id="queue-stats")
                        yield Static("", id="queue-progress")
                        yield DataTable(id="queue-table")
                    with TabPane("Sources", id="tab-sources"):
                        with Horizontal(id="sources-btn-row"):
                            yield Button("+ Add Endpoint", id="add-key-btn", variant="primary")
                        yield DataTable(id="sources-table")
                    with TabPane("News", id="tab-news"):
                        with Vertical(id="news-tab-content"):
                            with Horizontal(id="news-sources-header"):
                                yield Button("Refresh Sources from NewsAPI", id="refresh-sources-btn", variant="primary")
                                yield Input(placeholder="Filter by name or category...", id="source-filter")
                            yield DataTable(id="news-sources-table")
                            with Vertical(id="news-keywords-section"):
                                yield Static("Keywords", id="keywords-header")
                                with Horizontal(id="keyword-input-row"):
                                    yield Input(placeholder="Add keyword...", id="keyword-input")
                                    yield Button("Add", id="add-keyword-btn", variant="success")
                                    yield Button("Delete Selected", id="del-keyword-btn", variant="error")
                                yield DataTable(id="keywords-table")
        yield Footer()

    def on_mount(self) -> None:
        db.init_db()
        self._setup_queue_table()
        self._setup_sources_table()
        self._setup_news_tables()
        self._refresh_queue()
        self._refresh_sources()
        self._refresh_news_sources()
        self._refresh_keywords()
        self.set_interval(15, self._refresh_queue)
        self._log(f"[bold green]StackScreener Data Scraper ready.[/] {len(_COMMANDS)} commands available.")

    # ── helpers ────────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        self.query_one("#log", RichLog).write(msg)

    def _setup_queue_table(self) -> None:
        tbl = self.query_one("#queue-table", DataTable)
        for col in ("job_uid", "type", "status", "description", "priority", "retries", "created_at"):
            tbl.add_column(col, key=col)
        tbl.cursor_type = "row"

    def _setup_sources_table(self) -> None:
        tbl = self.query_one("#sources-table", DataTable)
        tbl.add_columns("role", "display name", "key (masked)", "url", "endpoint")
        tbl.cursor_type = "row"

    def _refresh_queue(self) -> None:
        self._refresh_queue_type_select()
        stats = db.get_llm_queue_stats()
        jobs  = db.get_llm_jobs(limit=200)
        label = "  ".join(f"{k}: {v}" for k, v in sorted(stats.items()))
        self.query_one("#queue-stats", Static).update(f"[bold]Queue:[/]  {label}")
        self.query_one("#queue-progress", Static).update(self._build_queue_progress(jobs))
        tbl = self.query_one("#queue-table", DataTable)
        tbl.clear()
        for j in jobs:
            status_markup = {
                "running":   "[bold cyan]running[/]",
                "done":      "[green]done[/]",
                "failed":    "[red]failed[/]",
                "paused":    "[yellow]paused[/]",
                "cancelled": "[dim]cancelled[/]",
                "pending":   "pending",
            }.get(j["status"], j["status"])
            tbl.add_row(
                str(j["job_uid"]),
                j["job_type"],
                status_markup,
                _job_description(j),
                str(j["priority"]),
                str(j["retries"]),
                str(j["created_at"] or "")[:16],
            )
        tbl.sort(self._queue_sort_col, reverse=not self._queue_sort_asc)
        pending = stats.get("pending", 0)
        running = stats.get("running", 0)
        self.query_one("#stats-bar", Label).update(
            f"Queue — pending: {pending}  running: {running}  "
            f"done: {stats.get('done', 0)}  failed: {stats.get('failed', 0)}"
        )

    def _build_queue_progress(self, jobs: list[dict]) -> str:
        """Per-type progress bars with ETA."""
        by_type: dict[str, Counter] = {}
        for j in jobs:
            t = j["job_type"]
            if t not in by_type:
                by_type[t] = Counter()
            by_type[t][j["status"]] += 1
        if not by_type:
            return ""
        lines: list[str] = []
        for jtype, counts in sorted(by_type.items()):
            total   = sum(counts.values())
            done    = counts.get("done", 0) + counts.get("failed", 0)
            pct     = done / total if total else 0
            filled  = int(pct * 24)
            bar     = "█" * filled + "░" * (24 - filled)
            eta     = self._queue_eta(jtype, counts, jobs)
            lines.append(f"[bold]{jtype}[/]  [cyan]{bar}[/]  {done}/{total}  {eta}")
        return "\n".join(lines)

    def _queue_eta(self, jtype: str, counts: Counter, jobs: list[dict]) -> str:
        """ETA string from average completed-job duration."""
        done_jobs = [
            j for j in jobs
            if j["job_type"] == jtype and j["status"] == "done"
            and j.get("started_at") and j.get("completed_at")
        ]
        pending = counts.get("pending", 0) + counts.get("running", 0)
        if not pending:
            failed = counts.get("failed", 0)
            return f"[green]complete[/]" + (f" [red]({failed} failed)[/]" if failed else "")
        if not done_jobs:
            return f"[dim]{pending} remaining[/]"
        durations: list[float] = []
        for j in done_jobs:
            try:
                s = datetime.fromisoformat(j["started_at"])
                e = datetime.fromisoformat(j["completed_at"])
                durations.append((e - s).total_seconds())
            except Exception:
                pass
        if not durations:
            return f"[dim]{pending} remaining[/]"
        avg   = statistics.mean(durations)
        secs  = int(pending * avg)
        eta   = f"~{secs}s" if secs < 120 else f"~{secs // 60}m{secs % 60:02d}s"
        return f"[yellow]{eta} remaining[/]  ({avg:.1f}s/job avg)"

    def _refresh_sources(self) -> None:
        rows = db.query("SELECT name, display_name, api_key, url, connector_config FROM api_keys ORDER BY name")
        tbl  = self.query_one("#sources-table", DataTable)
        tbl.clear()
        for r in rows:
            key_val  = str(r["api_key"] or "")
            masked   = f"****{key_val[-4:]}" if len(key_val) > 4 else "****"
            endpoint = "[green]configured[/]" if r["connector_config"] else "[dim]—[/]"
            tbl.add_row(
                r["name"], str(r["display_name"] or ""), masked,
                str(r["url"] or ""), endpoint,
                key=r["name"],
            )

    # ── News tab helpers ───────────────────────────────────────────────────────

    def _setup_news_tables(self) -> None:
        src_tbl = self.query_one("#news-sources-table", DataTable)
        src_tbl.add_columns("", "source id", "name", "category", "country")
        src_tbl.cursor_type = "row"
        kw_tbl = self.query_one("#keywords-table", DataTable)
        kw_tbl.add_columns("", "keyword")
        kw_tbl.cursor_type = "row"

    def _refresh_news_sources(self, filter_text: str = "") -> None:
        self._all_sources = db.get_newsapi_sources(1)
        self._render_news_sources(filter_text)

    def _render_news_sources(self, filter_text: str = "") -> None:
        tbl = self.query_one("#news-sources-table", DataTable)
        tbl.clear()
        ft = filter_text.lower()
        for s in self._all_sources:
            if ft and ft not in s["name"].lower() and ft not in (s["category"] or "").lower():
                continue
            check = "[green]✓[/]" if s["enabled"] else " "
            tbl.add_row(check, s["source_id"], s["name"], s["category"] or "", s["country"] or "",
                        key=s["source_id"])

    def _refresh_keywords(self) -> None:
        tbl = self.query_one("#keywords-table", DataTable)
        tbl.clear()
        for kw in db.get_newsapi_keywords(1):
            check = "[green]✓[/]" if kw["enabled"] else " "
            tbl.add_row(check, kw["keyword"], key=str(kw["keyword_uid"]))

    # ── button handlers ────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "worker-btn":
            self._toggle_worker()
            return

        if btn_id == "pause-jobs-btn":
            jt = self._selected_job_type()
            db.pause_llm_jobs(jt)
            label = jt or "all"
            self._log(f"[yellow]⏸ Paused pending jobs ({label})[/]")
            self._refresh_queue()
            return

        if btn_id == "resume-jobs-btn":
            jt = self._selected_job_type()
            db.resume_llm_jobs(jt)
            label = jt or "all"
            self._log(f"[green]▶ Resumed paused jobs ({label})[/]")
            self._refresh_queue()
            return

        if btn_id == "cancel-jobs-btn":
            jt = self._selected_job_type()
            db.cancel_llm_jobs(jt)
            label = jt or "all"
            self._log(f"[red]✕ Cancelled pending/paused jobs ({label})[/]")
            self._refresh_queue()
            return

        if btn_id == "set-priority-btn":
            jt = self._selected_job_type()
            if not jt:
                self._log("[yellow]Select a specific job type to set priority.[/]")
                return
            try:
                pri = int(self.query_one("#priority-input", Input).value.strip())
            except ValueError:
                self._log("[red]Priority must be 1–9.[/]")
                return
            db.set_job_priority(jt, pri)
            self._log(f"[cyan]Priority for '{jt}' set to {pri}[/]")
            self._refresh_queue()
            return

        if btn_id == "add-key-btn":
            self.push_screen(EndpointModal(), self._after_endpoint_edit)
            return

        if btn_id == "refresh-sources-btn":
            self._log("[bold cyan]▶ Refreshing NewsAPI source list...[/]")
            asyncio.get_event_loop().create_task(self._run_newsapi_refresh())
            return

        if btn_id == "add-keyword-btn":
            kw = self.query_one("#keyword-input", Input).value.strip()
            if kw:
                db.add_newsapi_keyword(1, kw)
                self.query_one("#keyword-input", Input).value = ""
                self._refresh_keywords()
                self._log(f"[green]Keyword added:[/] {kw}")
            return

        if btn_id == "del-keyword-btn":
            tbl = self.query_one("#keywords-table", DataTable)
            if tbl.cursor_row is not None:
                row_key = str(tbl.get_row_at(tbl.cursor_row)[1])
                kws = db.get_newsapi_keywords(1)
                match = next((k for k in kws if k["keyword"] == row_key), None)
                if match:
                    db.delete_newsapi_keyword(1, match["keyword_uid"])
                    self._refresh_keywords()
                    self._log(f"[yellow]Keyword deleted:[/] {row_key}")
            return

        # Match pipeline button by label
        for label, _desc, argv in _COMMANDS:
            if btn_id == _btn_id(label):
                self._run_command(label, argv)
                return

    def _toggle_worker(self) -> None:
        btn = self.query_one("#worker-btn", Button)
        if self._worker_proc and self._worker_proc.returncode is None:
            self._worker_proc.terminate()
            self._worker_proc = None
            btn.label   = "Start Worker"
            btn.variant = "success"
            self._log("[yellow]LLM worker stopped.[/]")
        else:
            argv = [sys.executable, f"{_SRC}/llm.py", "--worker"]
            limit_val = self.query_one("#worker-limit-input", Input).value.strip()
            if limit_val.isdigit():
                argv += ["--limit", limit_val]
            self._log(f"[bold]Starting LLM worker:[/] {' '.join(argv)}")
            self.run_worker_async(argv)
            btn.label   = "Stop Worker"
            btn.variant = "error"

    def _selected_job_type(self) -> str | None:
        """Return the currently selected job type filter, or None for All."""
        try:
            val = self.query_one("#queue-type-select", Select).value
            return str(val) if val else None
        except Exception:
            return None

    def _refresh_queue_type_select(self) -> None:
        """Sync the job-type dropdown with current distinct job types in queue."""
        try:
            sel = self.query_one("#queue-type-select", Select)
            types = db.get_distinct_job_types()
            options = [("All Types", "")] + [(t, t) for t in types]
            sel.set_options(options)
        except Exception:
            pass

    def run_worker_async(self, argv: list[str]) -> None:
        asyncio.get_event_loop().create_task(self._stream_worker(argv))

    async def _stream_worker(self, argv: list[str]) -> None:
        env = {**os.environ, "PYTHONPATH": _SRC, "PYTHONIOENCODING": "utf-8"}
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        self._worker_proc = proc
        assert proc.stdout
        async for line in proc.stdout:
            self._log(line.decode(errors="replace").rstrip())
        await proc.wait()
        self._log(f"[dim]Worker exited (code {proc.returncode})[/]")
        btn = self.query_one("#worker-btn", Button)
        btn.label   = "Start Worker"
        btn.variant = "success"

    def _run_command(self, label: str, argv: list[str]) -> None:
        self._log(f"\n[bold cyan]▶ {label}[/]  {' '.join(argv[1:])}")
        asyncio.get_event_loop().create_task(self._stream_command(label, argv))

    async def _stream_command(self, label: str, argv: list[str]) -> None:
        env = {**os.environ, "PYTHONPATH": _SRC, "PYTHONIOENCODING": "utf-8"}
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        self._active_proc = proc
        assert proc.stdout
        async for line in proc.stdout:
            self._log(line.decode(errors="replace").rstrip())
        await proc.wait()
        self._log(f"[dim]▶ {label} finished (code {proc.returncode})[/]\n")
        self._active_proc = None
        self._refresh_queue()

    def _after_endpoint_edit(self, result) -> None:
        self._refresh_sources()
        if result == "saved":
            self._log("[green]Endpoint saved.[/]")

    async def _run_newsapi_refresh(self) -> None:
        env = {**os.environ, "PYTHONPATH": _SRC, "PYTHONIOENCODING": "utf-8"}
        argv = [sys.executable, f"{_SRC}/news.py", "--newsapi-refresh"]
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        assert proc.stdout
        async for line in proc.stdout:
            self._log(line.decode(errors="replace").rstrip())
        await proc.wait()
        self._refresh_news_sources()
        self._refresh_keywords()
        self._log("[green]NewsAPI source list refreshed.[/]")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "source-filter":
            self._render_news_sources(event.value)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        if event.data_table.id == "queue-table":
            col = str(event.column_key.value) if event.column_key else None
            if col:
                if self._queue_sort_col == col:
                    self._queue_sort_asc = not self._queue_sort_asc
                else:
                    self._queue_sort_col = col
                    self._queue_sort_asc = True
                self._refresh_queue()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "sources-table":
            name = str(event.row_key.value)
            row = db.query_one(
                "SELECT name, display_name, role, url, connector_config "
                "FROM api_keys WHERE user_uid = 1 AND name = ?",
                (name,),
            )
            if row:
                self.push_screen(
                    EndpointModal(
                        name=row["name"],
                        current_key="",
                        current_display=row["display_name"] or "",
                        current_url=row["url"] or "",
                        current_config=row["connector_config"] or "",
                        current_role=row["role"] or "",
                    ),
                    self._after_endpoint_edit,
                )

        elif event.data_table.id == "news-sources-table":
            source_id = str(event.row_key.value)
            src = next((s for s in self._all_sources if s["source_id"] == source_id), None)
            if src:
                new_state = not src["enabled"]
                db.toggle_newsapi_source(1, source_id, new_state)
                filt = self.query_one("#source-filter", Input).value
                self._refresh_news_sources(filt)

        elif event.data_table.id == "keywords-table":
            tbl = event.data_table
            row_key = str(event.row_key.value)
            kws = db.get_newsapi_keywords(1)
            match = next((k for k in kws if str(k["keyword_uid"]) == row_key), None)
            if match:
                db.toggle_newsapi_keyword(1, match["keyword_uid"], not match["enabled"])
                self._refresh_keywords()


def main() -> None:
    db.init_db()
    ScraperApp().run()


if __name__ == "__main__":
    main()
