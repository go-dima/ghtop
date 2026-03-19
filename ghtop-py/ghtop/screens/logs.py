# ghtop/screens/logs.py
# Stub — full implementation in Task 10
from __future__ import annotations
from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class LogsScreen(Screen):
    def __init__(
        self,
        run_id: Optional[int],
        repo: str,
        job_name: str,
        pr_number: int,
        workflow_name: str,
    ) -> None:
        super().__init__()
        self._run_id = run_id
        self._repo = repo
        self._job_name = job_name
        self._pr_number = pr_number
        self._workflow_name = workflow_name

    def compose(self) -> ComposeResult:
        yield Static(
            f"Logs for {self._workflow_name} / {self._job_name} "
            f"(PR #{self._pr_number})"
        )
