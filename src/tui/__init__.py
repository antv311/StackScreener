"""
tui — StackScreener Bloomberg TUI package.

Import StackScreenerApp from here; all other classes are accessible via
their submodules (tui.modals, tui.tabs, tui.panels, tui.screens).
"""
from __future__ import annotations

from textual.app import App

import db
from .panels import MainScreen
from .screens import LoginScreen


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


__all__ = ["StackScreenerApp"]
