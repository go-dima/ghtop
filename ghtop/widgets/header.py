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
        background: $surface;
        border-bottom: tall $primary;
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
    loading: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="breadcrumb")
        yield Static("", id="error-banner")

    def _refresh_breadcrumb(self) -> None:
        try:
            text = self.breadcrumb
            if self.loading:
                text += "  ···"
            self.query_one("#breadcrumb", Static).update(text)
        except Exception:
            pass

    def watch_breadcrumb(self, value: str) -> None:
        self._refresh_breadcrumb()

    def watch_loading(self, value: bool) -> None:
        self._refresh_breadcrumb()

    def watch_error(self, value: str) -> None:
        try:
            banner = self.query_one("#error-banner", Static)
            banner.update(f"⚠ {value}" if value else "")
            if value:
                self.add_class("has-error")
            else:
                self.remove_class("has-error")
        except Exception:
            pass
