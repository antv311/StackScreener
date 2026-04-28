"""
app.py — StackScreener TUI entry point.

All application code lives in the tui/ subpackage.
"""
from tui import StackScreenerApp


def main() -> None:
    StackScreenerApp().run()


if __name__ == "__main__":
    main()
