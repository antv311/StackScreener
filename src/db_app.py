"""
db_app.py — P2 Database & Server TUI for StackScreener.

Provides a terminal UI for browsing database tables, running ad-hoc SELECT
queries, and viewing database statistics.

Usage:
    python src/db_app.py
"""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable, Footer, Header, Input, Label,
    ListView, ListItem, RichLog, Static, TabbedContent, TabPane,
)

import db
from screener_config import DB_PATH, DEBUG_MODE


# ── DB App ─────────────────────────────────────────────────────────────────────

class DBApp(App):
    """P2 Database TUI — table browser, SQL shell, DB stats."""

    TITLE    = "StackScreener — Database"
    CSS_PATH = None

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }
    #stats-bar {
        height: 1;
        background: $primary-darken-2;
        padding: 0 2;
        color: $text;
    }
    /* Browser tab */
    #browser-pane {
        layout: horizontal;
        height: 1fr;
    }
    #table-list {
        width: 24;
        background: $panel;
        border-right: solid $primary-darken-2;
    }
    #table-list ListItem {
        padding: 0 1;
    }
    #table-list ListItem:hover {
        background: $primary-darken-1;
    }
    #browser-right {
        width: 1fr;
    }
    #selected-label {
        height: 1;
        background: $surface;
        padding: 0 1;
        color: $text-muted;
    }
    #row-count-label {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    #pager-bar {
        height: 1;
        layout: horizontal;
        background: $panel;
        padding: 0 1;
    }
    DataTable {
        height: 1fr;
    }
    /* SQL shell tab */
    #sql-input {
        height: 3;
        border: solid $primary-darken-2;
        margin-bottom: 1;
    }
    RichLog {
        height: 1fr;
    }
    /* Stats tab */
    #stats-content {
        height: 1fr;
        padding: 1 2;
    }
    TabPane {
        padding: 1;
        height: 1fr;
    }
    """

    _PAGE_SIZE = 100
    _sql_history: list[str]
    _history_idx: int

    def __init__(self) -> None:
        super().__init__()
        self._current_table = ""
        self._offset        = 0
        self._sql_history   = []
        self._history_idx   = -1

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("", id="stats-bar")
        with TabbedContent():
            with TabPane("Browser", id="tab-browser"):
                with Horizontal(id="browser-pane"):
                    yield ListView(id="table-list")
                    with Vertical(id="browser-right"):
                        yield Label("Select a table →", id="selected-label")
                        yield Label("", id="row-count-label")
                        with Horizontal(id="pager-bar"):
                            yield Label("PgUp / PgDn to page", id="pager-hint")
                        yield DataTable(id="browse-table")
            with TabPane("SQL Shell", id="tab-sql"):
                yield Input(placeholder="SELECT ... (Enter to run, ↑/↓ for history)", id="sql-input")
                yield RichLog(id="sql-log", highlight=True, markup=True)
            with TabPane("Stats", id="tab-stats"):
                yield Static("", id="stats-content")
        yield Footer()

    def on_mount(self) -> None:
        db.init_db()
        self._load_table_list()
        self._update_stats_bar()
        self._render_stats_tab()

    # ── table browser ──────────────────────────────────────────────────────────

    def _load_table_list(self) -> None:
        lv     = self.query_one("#table-list", ListView)
        tables = db.get_table_names()
        for name in tables:
            lv.append(ListItem(Label(name), id=f"tbl-{name}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id.startswith("tbl-"):
            table_name = item_id[4:]
            self._current_table = table_name
            self._offset        = 0
            self._load_browse_page()

    def _load_browse_page(self) -> None:
        if not self._current_table:
            return
        try:
            rows = db.browse_table(self._current_table, self._PAGE_SIZE, self._offset)
        except ValueError as e:
            self.query_one("#selected-label", Label).update(f"[red]{e}[/]")
            return

        self.query_one("#selected-label", Label).update(
            f"[bold]{self._current_table}[/]  (offset {self._offset})"
        )

        tbl = self.query_one("#browse-table", DataTable)
        tbl.clear(columns=True)

        if not rows:
            self.query_one("#row-count-label", Label).update("No rows.")
            return

        cols = list(rows[0].keys())
        tbl.add_columns(*cols)
        for row in rows:
            tbl.add_row(*[str(row[c] if row[c] is not None else "") for c in cols])

        self.query_one("#row-count-label", Label).update(
            f"{len(rows)} rows (page {self._offset // self._PAGE_SIZE + 1})"
        )

    def on_key(self, event) -> None:
        # Pager navigation in Browser tab
        if event.key == "pagedown" and self._current_table:
            self._offset += self._PAGE_SIZE
            self._load_browse_page()
        elif event.key == "pageup" and self._current_table:
            self._offset = max(0, self._offset - self._PAGE_SIZE)
            self._load_browse_page()

        # SQL history navigation
        sql_input = self.query_one("#sql-input", Input)
        if sql_input.has_focus:
            if event.key == "up" and self._sql_history:
                self._history_idx = min(self._history_idx + 1, len(self._sql_history) - 1)
                sql_input.value   = self._sql_history[-(self._history_idx + 1)]
            elif event.key == "down" and self._sql_history:
                if self._history_idx > 0:
                    self._history_idx -= 1
                    sql_input.value = self._sql_history[-(self._history_idx + 1)]
                else:
                    self._history_idx = -1
                    sql_input.value   = ""

    # ── SQL shell ──────────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "sql-input":
            return
        sql = event.value.strip()
        if not sql:
            return
        self._sql_history.append(sql)
        self._history_idx = -1
        event.input.value = ""
        log = self.query_one("#sql-log", RichLog)
        log.write(f"\n[bold cyan]>[/] {sql}")
        try:
            rows = db.execute_raw_sql(sql)
            if not rows:
                log.write("[dim]No rows returned.[/]")
                return
            cols = list(rows[0].keys())
            # Simple tabular output
            sample = rows[:100]
            widths = {c: max(len(c), max(len(str(r[c] or "")) for r in sample)) for c in cols}
            widths = {c: min(w, 40) for c, w in widths.items()}
            header = "  ".join(c.ljust(widths[c]) for c in cols)
            sep    = "  ".join("─" * widths[c] for c in cols)
            log.write(f"[bold]{header}[/]")
            log.write(sep)
            for row in rows[:200]:
                line = "  ".join(str(row[c] or "")[:widths[c]].ljust(widths[c]) for c in cols)
                log.write(line)
            if len(rows) == 200:
                log.write("[dim](truncated at 200 rows)[/]")
            log.write(f"[dim]{len(rows)} row(s)[/]")
        except ValueError as e:
            log.write(f"[red]{e}[/]")
        except Exception as e:
            log.write(f"[red]Error: {e}[/]")

    # ── stats ──────────────────────────────────────────────────────────────────

    def _update_stats_bar(self) -> None:
        try:
            size_mb = Path(DB_PATH).stat().st_size / 1_048_576
            label   = f"DB: {DB_PATH}  ({size_mb:.1f} MB)"
        except FileNotFoundError:
            label = f"DB: {DB_PATH}  (not found)"
        self.query_one("#stats-bar", Label).update(label)

    def _render_stats_tab(self) -> None:
        tables = db.get_table_names()
        lines  = ["[bold]Table Row Counts[/]\n"]
        for t in tables:
            try:
                rows = db.execute_raw_sql(f"SELECT COUNT(*) AS cnt FROM {t}")
                cnt  = rows[0]["cnt"] if rows else 0
            except Exception:
                cnt  = "?"
            lines.append(f"  {t:<35} {cnt:>8}")

        try:
            size_mb = Path(DB_PATH).stat().st_size / 1_048_576
            lines.append(f"\n[bold]File[/]  {DB_PATH}  ({size_mb:.2f} MB)")
        except FileNotFoundError:
            pass

        try:
            indexes = db.execute_raw_sql(
                "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
            )
            lines.append(f"\n[bold]Indexes[/] ({len(indexes)} total)")
            for idx in indexes:
                lines.append(f"  {idx['name']}")
        except Exception:
            pass

        self.query_one("#stats-content", Static).update("\n".join(lines))


def main() -> None:
    db.init_db()
    DBApp().run()


if __name__ == "__main__":
    main()
