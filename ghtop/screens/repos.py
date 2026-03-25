# ghtop/screens/repos.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static

from ghtop.config import CONCURRENT_FETCH_LIMIT
from ghtop.gh import gh, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


def _format_age(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s ago"
        if s < 3600:
            return f"{s // 60}m ago"
        if s < 86400:
            return f"{s // 3600}h ago"
        return f"{s // 86400}d ago"
    except Exception:
        return "?"


@dataclass
class RepoItem:
    name: str
    updated_at: str
    open_prs: Optional[int] = None
    is_pinned: bool = False


class ReposScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("escape,backspace", "go_back", "Back"),
        Binding("p", "pin", "Pin"),
        Binding("slash", "search", "Search"),
        Binding("q", "quit_app", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    DEFAULT_CSS = """
    #repo-table {
        height: 1fr;
    }
    #info-line {
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, owner: str) -> None:
        super().__init__()
        self._owner = owner
        self._repos: list[RepoItem] = []
        self._filtered: list[RepoItem] = []
        self._searching = False

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Static("", id="info-line")
        yield Input(placeholder="Search repos...", id="search-input")
        yield DataTable(id="repo-table")
        yield StatusBar("", id="status-bar-widget")

    async def on_mount(self) -> None:
        header = self.query_one(AppHeader)
        header.breadcrumb = f"★ {self._owner} / repos"
        self.query_one("#search-input").display = False
        self.query_one("#info-line").display = False

        table = self.query_one(DataTable)
        table.add_columns("NAME", "OPEN PRS", "LAST ACTIVITY")
        self._update_status_bar(empty=False)
        self.run_worker(self._load_repos(), exclusive=True)

    async def _load_repos(self) -> None:
        header = self.query_one(AppHeader)
        header.loading = True
        try:
            await self._fetch_repos()
        finally:
            header.loading = False

    async def _fetch_repos(self) -> None:
        try:
            all_repos: list[dict] = await gh(
                "repo", "list", self._owner,
                "--limit", "20",
                "--json", "name,updatedAt",
            ) or []
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        if not all_repos:
            info = self.query_one("#info-line", Static)
            info.update(f"No repositories found in {self._owner}")
            info.display = True
            self._update_status_bar(empty=True)
            return

        self._repos = [
            RepoItem(
                name=r["name"],
                updated_at=r.get("updatedAt", ""),
                is_pinned=(
                    r["name"] == self.app.config.pinned_repo and
                    self._owner == self.app.config.pinned_owner
                ),
            )
            for r in all_repos
        ]

        # Fetch open PR counts concurrently
        sem = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)

        async def fetch_pr_count(repo: RepoItem) -> None:
            async with sem:
                try:
                    prs = await gh(
                        "pr", "list",
                        "--repo", f"{self._owner}/{repo.name}",
                        "--state", "open",
                        "--json", "number",
                    )
                    repo.open_prs = len(prs) if prs else 0
                except GHError:
                    repo.open_prs = None

        await asyncio.gather(*[fetch_pr_count(r) for r in self._repos])
        self._filtered = list(self._repos)
        info = self.query_one("#info-line", Static)
        info.update("")
        info.display = False
        self._update_status_bar(empty=False)
        self._render_table()
        self.query_one(DataTable).focus()

    def _update_status_bar(self, empty: bool) -> None:
        if empty:
            hints = "^r refresh  Esc back  q quit"
        else:
            hints = "↑↓ navigate  Enter select  / search  p pin  ^r refresh  Esc back  q quit"
        self.query_one("#status-bar-widget", StatusBar).update_hints(hints)

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for repo in self._filtered:
            pin = "★ " if repo.is_pinned else "  "
            prs = str(repo.open_prs) if repo.open_prs is not None else "?"
            age = _format_age(repo.updated_at)
            table.add_row(f"{pin}{repo.name}", prs, age)

    def action_select(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._filtered):
            return
        repo = self._filtered[row]
        from ghtop.screens.prs import PRsScreen
        self.app.push_screen(PRsScreen(self._owner, repo.name))

    def action_go_back(self) -> None:
        if self._searching:
            self._close_search()
        else:
            self.app.pop_screen()

    def action_pin(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._filtered):
            return
        repo = self._filtered[row]
        if repo.is_pinned:
            self.app.config.pinned_repo = None
            repo.is_pinned = False
        else:
            for r in self._repos:
                r.is_pinned = False
            self.app.config.pinned_owner = self._owner
            self.app.config.pinned_repo = repo.name
            repo.is_pinned = True
        self.app._save_config()
        self._render_table()

    def action_search(self) -> None:
        self._searching = True
        inp = self.query_one("#search-input", Input)
        inp.display = True
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if not query:
            self._filtered = list(self._repos)
        else:
            self._filtered = [r for r in self._repos if query in r.name.lower()]
        self._render_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._close_search()

    def _close_search(self) -> None:
        self._searching = False
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.display = False
        self._filtered = list(self._repos)
        self._render_table()
        self.query_one(DataTable).focus()

    def action_refresh(self) -> None:
        self.run_worker(self._load_repos(), exclusive=True)

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
