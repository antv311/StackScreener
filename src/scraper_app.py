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
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    RichLog, Static, TabbedContent, TabPane,
)
from textual.screen import ModalScreen

import db
from screener_config import DEBUG_MODE

def _btn_id(label: str) -> str:
    """Convert a button label to a valid Textual CSS identifier."""
    return "btn-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


# ── Pipeline command definitions ───────────────────────────────────────────────

_SRC = str(Path(__file__).parent)

_COMMANDS: list[tuple[str, str, list[str]]] = [
    # (button label, description, argv relative to venv python)
    ("Enrich Fundamentals",   "enricher.py",              [sys.executable, f"{_SRC}/enricher.py"]),
    ("EDGAR CIKs",            "edgar.py --seed-ciks",      [sys.executable, f"{_SRC}/edgar.py", "--seed-ciks"]),
    ("EDGAR XBRL Facts",      "edgar.py --fetch-facts",    [sys.executable, f"{_SRC}/edgar.py", "--fetch-facts", "--limit", "100"]),
    ("EDGAR 10-K Text",       "edgar.py --fetch-filings",  [sys.executable, f"{_SRC}/edgar.py", "--fetch-filings", "--limit", "50"]),
    ("EDGAR 8-K Events",      "edgar.py --fetch-8k",       [sys.executable, f"{_SRC}/edgar.py", "--fetch-8k", "--limit", "100"]),
    ("Form 4 Insider Trades", "inst_flow.py --form4",      [sys.executable, f"{_SRC}/inst_flow.py", "--form4"]),
    ("Form 13F Holdings",     "inst_flow.py --form13f",    [sys.executable, f"{_SRC}/inst_flow.py", "--form13f"]),
    ("Options Flow",          "inst_flow.py --options",    [sys.executable, f"{_SRC}/inst_flow.py", "--options"]),
    ("News — All Sources",    "news.py --all",             [sys.executable, f"{_SRC}/news.py", "--all"]),
    ("News — Classify",       "news.py --classify",        [sys.executable, f"{_SRC}/news.py", "--classify"]),
    ("USDA Crop Conditions",  "commodities.py --usda",     [sys.executable, f"{_SRC}/commodities.py", "--usda-crops"]),
    ("EIA Petroleum",         "commodities.py --eia",      [sys.executable, f"{_SRC}/commodities.py", "--eia-petroleum"]),
    ("AIS Chokepoints",       "logistics.py --choke",      [sys.executable, f"{_SRC}/logistics.py", "--chokepoints"]),
    ("Panama Canal",          "logistics.py --panama",     [sys.executable, f"{_SRC}/logistics.py", "--panama"]),
    ("Supply Chain Seed",     "supply_chain.py --seed",    [sys.executable, f"{_SRC}/supply_chain.py", "--seed-tier2"]),
]


# ── API Key Modal ──────────────────────────────────────────────────────────────

class APIKeyModal(ModalScreen):
    """Add or edit an API key. Pass provider='' to show the provider name input."""

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(self, provider: str, current_key: str) -> None:
        super().__init__()
        self._provider    = provider
        self._current_key = current_key
        self._is_new      = provider == ""

    def compose(self) -> ComposeResult:
        title = "Add API Key" if self._is_new else f"Edit Key — {self._provider}"
        with Vertical(id="modal-box"):
            yield Static(title, id="modal-title")
            if self._is_new:
                yield Input(placeholder="Provider name (e.g. newsapi, aisstream)...", id="provider-input")
            yield Input(value=self._current_key, placeholder="API key...", id="key-input")
            with Horizontal(id="modal-buttons"):
                yield Button("Save",   variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            if self._is_new:
                provider = self.query_one("#provider-input", Input).value.strip()
            else:
                provider = self._provider
            new_key = self.query_one("#key-input", Input).value.strip()
            if provider and new_key:
                db.set_api_key(1, provider, new_key)
        self.dismiss()

    DEFAULT_CSS = """
    APIKeyModal {
        align: center middle;
    }
    #modal-box {
        width: 60;
        height: auto;
        padding: 2 3;
        background: $surface;
        border: thick $primary;
    }
    #modal-title {
        text-align: center;
        color: $accent;
        margin-bottom: 1;
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
        margin: 0 1 0 1;
        height: 1;
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
    #add-key-btn {
        width: auto;
        margin-bottom: 1;
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
            with Vertical(id="main-area"):
                yield Label("", id="stats-bar")
                with TabbedContent():
                    with TabPane("Logs", id="tab-logs"):
                        yield RichLog(id="log", highlight=True, markup=True)
                    with TabPane("Queue", id="tab-queue"):
                        yield Static("", id="queue-stats")
                        yield DataTable(id="queue-table")
                    with TabPane("Sources", id="tab-sources"):
                        yield Button("+ Add Key", id="add-key-btn", variant="primary")
                        yield DataTable(id="sources-table")
        yield Footer()

    def on_mount(self) -> None:
        db.init_db()
        self._setup_queue_table()
        self._setup_sources_table()
        self._refresh_queue()
        self._refresh_sources()
        self.set_interval(5, self._refresh_queue)
        self._log(f"[bold green]StackScreener Data Scraper ready.[/] {len(_COMMANDS)} commands available.")

    # ── helpers ────────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        self.query_one("#log", RichLog).write(msg)

    def _setup_queue_table(self) -> None:
        tbl = self.query_one("#queue-table", DataTable)
        tbl.add_columns("job_uid", "type", "status", "priority", "retries", "source_ref", "created_at")

    def _setup_sources_table(self) -> None:
        tbl = self.query_one("#sources-table", DataTable)
        tbl.add_columns("provider", "key (masked)", "url")
        tbl.cursor_type = "row"

    def _refresh_queue(self) -> None:
        stats = db.get_llm_queue_stats()
        jobs  = db.get_llm_jobs(limit=100)
        label = "  ".join(f"{k}: {v}" for k, v in sorted(stats.items()))
        self.query_one("#queue-stats", Static).update(f"[bold]Queue:[/]  {label}")
        tbl = self.query_one("#queue-table", DataTable)
        tbl.clear()
        for j in jobs:
            tbl.add_row(
                str(j["job_uid"]),
                j["job_type"],
                j["status"],
                str(j["priority"]),
                str(j["retries"]),
                str(j["source_ref"] or ""),
                str(j["created_at"] or "")[:16],
            )
        # Update stats bar
        pending = stats.get("pending", 0)
        running = stats.get("running", 0)
        self.query_one("#stats-bar", Label).update(
            f"Queue — pending: {pending}  running: {running}  done: {stats.get('done', 0)}  failed: {stats.get('failed', 0)}"
        )

    def _refresh_sources(self) -> None:
        rows = db.query("SELECT name, api_key, url FROM api_keys ORDER BY name")
        tbl  = self.query_one("#sources-table", DataTable)
        tbl.clear()
        for r in rows:
            key_val = str(r["api_key"] or "")
            masked  = f"****{key_val[-4:]}" if len(key_val) > 4 else "****"
            tbl.add_row(r["name"], masked, str(r["url"] or ""))

    # ── button handlers ────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "worker-btn":
            self._toggle_worker()
            return

        if btn_id == "add-key-btn":
            self.push_screen(APIKeyModal("", ""), self._after_key_edit)
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
            self._log(f"[bold]Starting LLM worker:[/] {' '.join(argv)}")
            self.run_worker_async(argv)
            btn.label   = "Stop Worker"
            btn.variant = "error"

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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "sources-table":
            row_key = event.row_key
            rows = db.query("SELECT name, url FROM api_keys ORDER BY name")
            idx = list(event.data_table.rows.keys()).index(row_key)
            if 0 <= idx < len(rows):
                provider = rows[idx]["name"]
                self.push_screen(APIKeyModal(provider, ""), self._after_key_edit)

    def _after_key_edit(self, _result) -> None:
        self._refresh_sources()


def main() -> None:
    db.init_db()
    ScraperApp().run()


if __name__ == "__main__":
    main()
