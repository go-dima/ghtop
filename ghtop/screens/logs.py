# ghtop/screens/logs.py
from __future__ import annotations
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static

from ghtop.gh import gh_raw, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


def filter_log_lines(raw: str, job_name: str) -> list[str]:
    """Filter log lines by exact match on first tab-delimited field."""
    result = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[0] == job_name:
            result.append(parts[2])
    return result


class LogsScreen(Screen):
    BINDINGS = [
        Binding("escape,backspace", "go_back", "Back"),
        Binding("slash", "search", "Search"),
        Binding("q", "quit_app", "Quit"),
    ]

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
        self._all_lines: list[str] = []
        self._searching = False

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Input(placeholder="Search logs...", id="search-input")
        yield RichLog(id="log-view", highlight=True, markup=False)
        yield Static("", id="empty-state")
        yield StatusBar("↑↓ scroll  / search  Esc back  q quit")

    async def on_mount(self) -> None:
        self.query_one(AppHeader).breadcrumb = (
            f"PR #{self._pr_number} · {self._workflow_name} · {self._job_name}"
        )
        self.query_one("#search-input").display = False
        self.query_one(RichLog).focus()
        await self._load_logs()

    async def _load_logs(self) -> None:
        if not self._run_id:
            self.query_one("#empty-state", Static).update("No run ID available.")
            return
        log_view = self.query_one(RichLog)
        header = self.query_one(AppHeader)
        header.loading = True
        try:
            try:
                raw = await gh_raw(
                    "run", "view", str(self._run_id),
                    "--repo", self._repo,
                    "--log",
                )
            except GHError as e:
                header.error = str(e)
                return
            self._all_lines = filter_log_lines(raw, self._job_name)
            self._render_logs(self._all_lines)
        finally:
            header.loading = False

    def _render_logs(self, lines: list[str]) -> None:
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        if not lines:
            self.query_one("#empty-state", Static).update(
                f"No log lines found for job: {self._job_name}"
            )
            return
        self.query_one("#empty-state", Static).update("")
        for line in lines:
            log_view.write(line)

    def action_search(self) -> None:
        self._searching = True
        inp = self.query_one("#search-input", Input)
        inp.display = True
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if not query:
            self._render_logs(self._all_lines)
        else:
            filtered = [l for l in self._all_lines if query in l.lower()]
            self._render_logs(filtered)

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._close_search()

    def _close_search(self) -> None:
        self._searching = False
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.display = False
        self._render_logs(self._all_lines)
        self.query_one(RichLog).focus()

    def action_go_back(self) -> None:
        if self._searching:
            self._close_search()
        else:
            self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()
