"""
tui/screens.py — LoginScreen and ChangePasswordScreen.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Input, Label

import db
from .panels import MainScreen


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
