# ghtop/widgets/status_bar.py
from __future__ import annotations
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    """Keybinding hints shown at the bottom of each screen."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary-darken-2;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def __init__(self, hints: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._hints = hints

    def compose(self) -> ComposeResult:
        yield Static(self._hints)

    def update_hints(self, hints: str) -> None:
        self.query_one(Static).update(hints)
