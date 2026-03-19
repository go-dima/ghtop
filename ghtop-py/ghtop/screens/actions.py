# ghtop/screens/actions.py
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Static

from ghtop.config import ACTIONS_REFRESH_INTERVAL
from ghtop.gh import gh, GHError
from ghtop.screens.prs import derive_pr_status, STATUS_ICON, _format_age
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


def _format_duration(started: Optional[str], completed: Optional[str]) -> str:
    if not started:
        return "—"
    try:
        start = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end = (datetime.fromisoformat(completed.replace("Z", "+00:00"))
               if completed else datetime.now(timezone.utc))
        secs = int((end - start).total_seconds())
        return f"{secs // 60}m {secs % 60}s"
    except Exception:
        return "?"


class ActionsScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "view_logs", "View Logs"),
        Binding("escape,backspace", "go_back", "Back"),
        Binding("t", "rerun", "Rerun"),
        Binding("r", "open_run_browser", "Open Run"),
        Binding("l", "open_job_browser", "Open Job"),
        Binding("o", "open_pr_browser", "Open PR"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, org: str, repo: str, pr: dict) -> None:
        super().__init__()
        self._org = org
        self._repo = repo
        self._pr = pr
        self._jobs: list[dict] = []
        self._run_id: Optional[int] = None
        self._scroll_row: int = 0
        self._pending_rerun: bool = False
        self._pending_rerun_timer: Optional[Timer] = None
        self._poll_worker = None

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Static("", id="pr-meta")
        yield DataTable(id="jobs-table")
        yield Static("", id="empty-state")
        yield StatusBar("t×2 rerun  l job browser  r run browser  o PR  Esc back  q quit")

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("WORKFLOW", "JOB", "STATUS", "DURATION")
        table.focus()
        await self._load_jobs()
        self._start_poll()

    def _start_poll(self) -> None:
        async def poll() -> None:
            while True:
                await asyncio.sleep(ACTIONS_REFRESH_INTERVAL)
                if self.is_attached:
                    await self._load_jobs()

        self._poll_worker = self.run_worker(poll(), exclusive=True)

    def on_unmount(self) -> None:
        if self._poll_worker:
            self._poll_worker.cancel()
        if self._pending_rerun_timer:
            self._pending_rerun_timer.stop()

    async def _load_jobs(self) -> None:
        runs = self._pr.get("_runs", [])
        if not runs:
            try:
                runs = await gh(
                    "run", "list",
                    "--repo", f"{self._org}/{self._repo}",
                    "--branch", self._pr.get("headRefName", ""),
                    "--limit", "1",
                    "--json", "databaseId,name,status,conclusion,startedAt,updatedAt",
                ) or []
            except GHError as e:
                self.query_one(AppHeader).error = str(e)
                return

        if not runs:
            self.query_one("#empty-state", Static).update(
                "No workflow runs found for this PR"
            )
            self._update_header([])
            return

        latest_run = runs[0]
        self._run_id = latest_run["databaseId"]

        try:
            run_detail = await gh(
                "run", "view", str(self._run_id),
                "--repo", f"{self._org}/{self._repo}",
                "--json", "jobs",
            )
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        self._jobs = (run_detail or {}).get("jobs", [])
        self._render_table()
        self._update_header(self._jobs)
        self.query_one(AppHeader).error = ""

    def _update_header(self, jobs: list[dict]) -> None:
        pr = self._pr
        status = derive_pr_status(jobs) if jobs else "unknown"
        icon, _ = STATUS_ICON.get(status, ("?", "gray"))
        age = _format_age(pr.get("createdAt", ""))
        breadcrumb = (
            f"PR #{pr['number']}: {pr['title'][:50]}   "
            f"{icon} {status}   "
            f"{self._org}/{self._repo} · {pr['author']['login']} · {age}"
        )
        self.query_one(AppHeader).breadcrumb = breadcrumb

        reviewers = [
            r.get("requestedReviewer", {}).get("login", "")
            for r in pr.get("reviewRequests", [])
        ]
        labels = [lbl["name"] for lbl in pr.get("labels", [])]
        meta_parts = []
        if reviewers:
            meta_parts.append("reviewers: " + ", ".join(r for r in reviewers if r))
        if labels:
            meta_parts.append("labels: " + " ".join(f"[{l}]" for l in labels))
        self.query_one("#pr-meta", Static).update("  ·  ".join(meta_parts))

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        if not self._jobs:
            return
        for job in self._jobs:
            status = job.get("status", "")
            conclusion = job.get("conclusion")
            state = conclusion if status == "completed" and conclusion else status
            icon, _ = STATUS_ICON.get(state, ("?", "gray"))
            duration = _format_duration(
                job.get("startedAt"), job.get("completedAt")
            )
            table.add_row(
                job.get("workflowName", ""),
                job.get("name", ""),
                f"{icon} {state}",
                duration,
            )
        if self._scroll_row < len(self._jobs):
            table.move_cursor(row=self._scroll_row)

    def action_view_logs(self) -> None:
        row = self.query_one(DataTable).cursor_row
        self._scroll_row = row
        if row >= len(self._jobs):
            return
        job = self._jobs[row]
        from ghtop.screens.logs import LogsScreen
        self.app.push_screen(LogsScreen(
            run_id=self._run_id,
            repo=f"{self._org}/{self._repo}",
            job_name=job.get("name", ""),
            pr_number=self._pr["number"],
            workflow_name=job.get("workflowName", ""),
        ))

    def action_rerun(self) -> None:
        if self._pending_rerun:
            if self._pending_rerun_timer:
                self._pending_rerun_timer.stop()
                self._pending_rerun_timer = None
            self._pending_rerun = False
            if self._run_id:
                self.run_worker(self._do_rerun(), exclusive=False)
        else:
            self._pending_rerun = True
            self._pending_rerun_timer = self.set_timer(
                3.0, self._cancel_pending_rerun
            )
            self.notify("Press t again to rerun failed jobs", severity="warning")

    async def _do_rerun(self) -> None:
        try:
            await gh("run", "rerun", str(self._run_id),
                     "--repo", f"{self._org}/{self._repo}", "--failed")
            self.notify("Rerun triggered", severity="information")
            await asyncio.sleep(2)
            await self._load_jobs()
        except GHError as e:
            self.notify(f"Rerun failed: {e}", severity="error")

    def _cancel_pending_rerun(self) -> None:
        self._pending_rerun = False
        self._pending_rerun_timer = None

    def action_open_run_browser(self) -> None:
        if self._run_id:
            self.run_worker(self._open_run(self._run_id), exclusive=False)

    async def _open_run(self, run_id: int) -> None:
        try:
            await gh("run", "view", str(run_id),
                     "--repo", f"{self._org}/{self._repo}", "--web")
        except GHError as e:
            self.notify(f"Could not open browser: {e}", severity="warning")

    def action_open_job_browser(self) -> None:
        if self._run_id:
            self.run_worker(self._open_run(self._run_id), exclusive=False)

    def action_open_pr_browser(self) -> None:
        self.run_worker(self._open_pr(), exclusive=False)

    async def _open_pr(self) -> None:
        try:
            await gh("pr", "view", str(self._pr["number"]),
                     "--repo", f"{self._org}/{self._repo}", "--web")
        except GHError as e:
            self.notify(f"Could not open browser: {e}", severity="warning")

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self.run_worker(self._load_jobs(), exclusive=True)

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
