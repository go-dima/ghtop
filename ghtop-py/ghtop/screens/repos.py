# ghtop/screens/repos.py
# Stub — full implementation in Task 7
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class ReposScreen(Screen):
    def __init__(self, org: str) -> None:
        super().__init__()
        self._org = org

    def compose(self) -> ComposeResult:
        yield Static(f"Repos for {self._org}")
