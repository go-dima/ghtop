# ghtop/widgets/header.py
from __future__ import annotations
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class AppHeader(Widget):
    """Breadcrumb + refresh indicator + error banner."""

    DEFAULT_CSS = """
    AppHeader {
        height: auto;
        background: $primary;
        padding: 0 1;
    }
    #error-banner {
        color: $error;
        display: none;
    }
    AppHeader.has-error #error-banner {
        display: block;
    }
    """

    breadcrumb: reactive[str] = reactive("")
    error: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("", id="breadcrumb")
        yield Static("", id="error-banner")

    def watch_breadcrumb(self, value: str) -> None:
        self.query_one("#breadcrumb", Static).update(value)

    def watch_error(self, value: str) -> None:
        banner = self.query_one("#error-banner", Static)
        banner.update(f"⚠ {value}" if value else "")
        if value:
            self.add_class("has-error")
        else:
            self.remove_class("has-error")
