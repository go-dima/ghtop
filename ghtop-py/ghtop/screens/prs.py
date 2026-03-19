# ghtop/screens/prs.py
# Stub — full implementation in Task 8
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class PRsScreen(Screen):
    def __init__(self, org: str, repo: str) -> None:
        super().__init__()
        self._org = org
        self._repo = repo

    def compose(self) -> ComposeResult:
        yield Static(f"PRs for {self._org}/{self._repo}")
