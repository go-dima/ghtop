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

    def __init__(self, org: str) -> None:
        super().__init__()
        self._org = org
        self._repos: list[RepoItem] = []
        self._filtered: list[RepoItem] = []
        self._searching = False

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Input(placeholder="Search repos...", id="search-input")
        yield DataTable(id="repo-table")
        yield Static("", id="empty-state")
        yield StatusBar(f"★ {self._org} / repos   Esc back  / search  p pin")

    async def on_mount(self) -> None:
        header = self.query_one(AppHeader)
        header.breadcrumb = f"★ {self._org} / repos"
        self.query_one("#search-input").display = False

        table = self.query_one(DataTable)
        table.add_columns("NAME", "OPEN PRS", "LAST ACTIVITY")
        await self._load_repos()

    async def _load_repos(self) -> None:
        all_repos: list[dict] = []
        try:
            while True:
                batch = await gh(
                    "repo", "list", self._org,
                    "--limit", "20",
                    "--json", "name,updatedAt",
                )
                if not batch:
                    break
                all_repos.extend(batch)
                if len(batch) < 20:
                    break
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        if not all_repos:
            self.query_one("#empty-state", Static).update(
                f"No repositories found in {self._org}"
            )
            return

        self._repos = [
            RepoItem(
                name=r["name"],
                updated_at=r.get("updatedAt", ""),
                is_pinned=(
                    r["name"] == self.app.config.pinned_repo and
                    self._org == self.app.config.pinned_org
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
                        "--repo", f"{self._org}/{repo.name}",
                        "--state", "open",
                        "--json", "number",
                    )
                    repo.open_prs = len(prs) if prs else 0
                except GHError:
                    repo.open_prs = None

        await asyncio.gather(*[fetch_pr_count(r) for r in self._repos])
        self._filtered = list(self._repos)
        self._render_table()

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
        self.app.push_screen(PRsScreen(self._org, repo.name))

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
            self.app.config.pinned_org = self._org
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
