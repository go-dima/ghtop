# ghtop/screens/prs.py
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static
from textual.worker import Worker

from ghtop.config import CONCURRENT_FETCH_LIMIT
from ghtop.gh import gh, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


STATUS_ICON = {
    "in_progress": ("⟳", "blue"),
    "queued": ("○", "blue"),
    "waiting": ("○", "blue"),
    "success": ("✓", "green"),
    "failure": ("✗", "red"),
    "timed_out": ("✗", "red"),
    "action_required": ("✗", "red"),
    "cancelled": ("⊘", "orange"),
    "stale": ("⊘", "orange"),
    "skipped": ("○", "gray"),
}


def derive_pr_status(jobs: list[dict]) -> str:
    """Derive overall PR status from job list per spec priority rules."""
    statuses = [j.get("status") for j in jobs]
    conclusions = [j.get("conclusion") for j in jobs]

    if any(s == "in_progress" for s in statuses):
        return "in_progress"
    if any(s in ("queued", "waiting") for s in statuses):
        return "queued"
    if any(c in ("failure", "timed_out", "action_required") for c in conclusions):
        return "failure"
    if any(c in ("cancelled", "stale") for c in conclusions):
        return "cancelled"
    if all(c == "success" for c in conclusions if c):
        return "success"
    return "unknown"


def _format_age(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s"
        if s < 3600:
            return f"{s // 60}m"
        if s < 86400:
            return f"{s // 3600}h"
        return f"{s // 86400}d"
    except Exception:
        return "?"


class PRsScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("escape,backspace", "go_back", "Back"),
        Binding("m", "toggle_filter", "My PRs"),
        Binding("slash", "search", "Search"),
        Binding("o", "open_browser", "Open PR"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, owner: str, repo: str) -> None:
        super().__init__()
        self._owner = owner
        self._repo = repo
        self._filter_mine: bool = True
        self._prs: list[dict] = []
        self._filtered: list[dict] = []
        self._worker: Optional[Worker] = None
        self._scroll_row: int = 0
        self._searching = False

    DEFAULT_CSS = """
    #pr-table {
        height: 1fr;
    }
    #info-line {
        color: $text-muted;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Static("", id="info-line")
        yield Input(placeholder="Search PRs...", id="search-input")
        yield DataTable(id="pr-table")
        yield StatusBar("", id="status-bar-widget")

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("#", "TITLE", "AUTHOR", "AGE", "✓", "⟳", "✗", "⊘", "Σ")
        self.query_one("#search-input").display = False
        self.query_one("#info-line").display = False
        self._update_header()
        self.run_worker(self._load_prs(), exclusive=True)
        self._start_poll()

    def _update_header(self, empty: bool = False) -> None:
        header = self.query_one(AppHeader)
        label = "My PRs" if self._filter_mine else "PRs"
        header.breadcrumb = f"★ {self._owner}/{self._repo} / {label}"
        if empty:
            hint_m = "m=all" if self._filter_mine else "m=mine"
            self.query_one("#status-bar-widget", StatusBar).update_hints(
                f"{hint_m}  ^r refresh  Esc back  q quit"
            )
        else:
            hint_m = "m=all" if self._filter_mine else "m=mine"
            self.query_one("#status-bar-widget", StatusBar).update_hints(
                f"↑↓ navigate  Enter PR  {hint_m}  / search  ^r refresh  Esc back  q quit"
            )

    def _start_poll(self) -> None:
        interval = self.app.config.refresh_interval

        async def poll() -> None:
            while True:
                await asyncio.sleep(interval)
                if self.is_attached:
                    await self._load_prs()

        self._worker = self.run_worker(poll(), exclusive=False)

    def on_unmount(self) -> None:
        if self._worker:
            self._worker.cancel()

    async def _load_prs(self) -> None:
        header = self.query_one(AppHeader)
        header.loading = True
        try:
            await self._fetch_prs()
        finally:
            header.loading = False

    async def _fetch_prs(self) -> None:
        limit = self.app.config.pr_limit
        repo_flag = f"{self._owner}/{self._repo}"
        base_args = [
            "pr", "list", "--repo", repo_flag,
            "--state", "open", "--limit", str(limit),
            "--json", "number,title,author,createdAt,headRefName,labels,reviewRequests",
        ]

        try:
            if self._filter_mine:
                authored, review_req = await asyncio.gather(
                    gh(*base_args, "--author", "@me"),
                    gh(*base_args, "--search", "review-requested:@me"),
                )
                seen: set[int] = set()
                merged: list[dict] = []
                for pr in (authored or []) + (review_req or []):
                    if pr["number"] not in seen:
                        seen.add(pr["number"])
                        merged.append(pr)
                prs = merged[:limit]
            else:
                prs = await gh(*base_args) or []
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        # Fetch run status concurrently
        sem = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)

        async def fetch_run_status(pr: dict) -> None:
            async with sem:
                try:
                    runs = await gh(
                        "run", "list",
                        "--repo", repo_flag,
                        "--branch", pr["headRefName"],
                        "--limit", "10",
                        "--json", "databaseId,name,status,conclusion,startedAt,updatedAt",
                    )
                    pr["_runs"] = runs or []
                except GHError:
                    pr["_runs"] = []

        await asyncio.gather(*[fetch_run_status(pr) for pr in prs])

        self._prs = prs
        self._filtered = list(prs)
        self._render_table()
        self.query_one(AppHeader).error = ""
        self.query_one(DataTable).focus()

    def _run_counts(self, pr: dict) -> tuple[int, int, int, int, int]:
        runs = pr.get("_runs", [])
        if not runs:
            return 0, 0, 0, 0, 0
        # Latest run per workflow (by name)
        latest: dict[str, dict] = {}
        for run in runs:
            name = run["name"]
            if name not in latest:
                latest[name] = run
        jobs = list(latest.values())
        success = sum(1 for j in jobs if j.get("conclusion") == "success")
        running = sum(1 for j in jobs if j.get("status") == "in_progress")
        failed = sum(1 for j in jobs
                     if j.get("conclusion") in ("failure", "timed_out", "action_required"))
        cancelled = sum(1 for j in jobs
                        if j.get("conclusion") in ("cancelled", "stale"))
        total = len(jobs)
        return success, running, failed, cancelled, total

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        info = self.query_one("#info-line", Static)
        if not self._filtered:
            msg = (
                "No open pull requests in this repo"
                if not self._filter_mine
                else "No open PRs authored by you or awaiting your review"
            )
            info.update(msg)
            info.display = True
            self._update_header(empty=True)
            return
        info.update("")
        info.display = False
        self._update_header(empty=False)
        for pr in self._filtered:
            s, r, f, c, total = self._run_counts(pr)
            age = _format_age(pr.get("createdAt", ""))
            table.add_row(
                f"#{pr['number']}",
                pr["title"][:60],
                pr["author"]["login"],
                age,
                str(s), str(r), str(f), str(c), str(total),
            )
        if self._scroll_row < len(self._filtered):
            table.move_cursor(row=self._scroll_row)

    def action_select(self) -> None:
        row = self.query_one(DataTable).cursor_row
        self._scroll_row = row
        if row >= len(self._filtered):
            return
        pr = self._filtered[row]
        from ghtop.screens.actions import ActionsScreen
        self.app.push_screen(ActionsScreen(
            owner=self._owner, repo=self._repo, pr=pr
        ))

    def action_go_back(self) -> None:
        if self._searching:
            self._close_search()
        else:
            self.app.pop_screen()

    def action_toggle_filter(self) -> None:
        self._filter_mine = not self._filter_mine
        self._update_header()
        self.run_worker(self._load_prs(), exclusive=True)

    def action_open_browser(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._filtered):
            return
        pr = self._filtered[row]
        self.run_worker(self._open_pr_browser(pr["number"]), exclusive=False)

    async def _open_pr_browser(self, number: int) -> None:
        try:
            await gh("pr", "view", str(number),
                     "--repo", f"{self._owner}/{self._repo}", "--web")
        except GHError as e:
            self.notify(f"Could not open browser. Error: {e}", severity="warning")

    def action_search(self) -> None:
        self._searching = True
        inp = self.query_one("#search-input", Input)
        inp.display = True
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if not query:
            self._filtered = list(self._prs)
        else:
            self._filtered = [
                pr for pr in self._prs
                if (query in pr["title"].lower() or
                    query in str(pr["number"]) or
                    query in pr["author"]["login"].lower())
            ]
        self._render_table()

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._close_search()

    def _close_search(self) -> None:
        self._searching = False
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.display = False
        self._filtered = list(self._prs)
        self._render_table()
        self.query_one(DataTable).focus()

    def action_refresh(self) -> None:
        self.run_worker(self._load_prs(), exclusive=True)

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
