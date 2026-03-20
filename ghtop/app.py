# ghtop/app.py
from __future__ import annotations
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from ghtop.config import load_config, save_config, DEFAULT_CONFIG_PATH, Config
from ghtop.gh import gh, gh_raw, GHError


class ErrorScreen(Screen):
    """Full-screen error shown when gh is not available or not authenticated."""

    BINDINGS = [("q", "quit_app", "Quit")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Static(self._message, id="error-message")

    def action_quit_app(self) -> None:
        self.app.exit()


class GHTopApp(App):
    """Root application — handles startup checks and initial routing."""

    CSS = """
    #error-message {
        padding: 2 4;
        color: $error;
    }
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        super().__init__()
        self._config_path = config_path
        self.config: Config = load_config(config_path) if config_path else load_config()

    async def on_mount(self) -> None:
        import shutil
        if not shutil.which("gh"):
            self.push_screen(ErrorScreen(
                "gh CLI not found. Install from https://cli.github.com"
            ))
            return

        try:
            await gh_raw("auth", "status")
        except GHError:
            self.push_screen(ErrorScreen(
                "Not authenticated. Run: gh auth login"
            ))
            return

        await self._route_to_start()

    async def _route_to_start(self) -> None:
        from ghtop.screens.orgs import OrgScreen
        from ghtop.screens.repos import ReposScreen
        from ghtop.screens.prs import PRsScreen

        if self.config.pinned_repo and self.config.pinned_org:
            try:
                await gh("repo", "view",
                         f"{self.config.pinned_org}/{self.config.pinned_repo}",
                         "--json", "name")
                self.push_screen(PRsScreen(self.config.pinned_org, self.config.pinned_repo))
                return
            except GHError:
                self.notify(
                    f"Pinned repo {self.config.pinned_org}/{self.config.pinned_repo} not found — clearing pin",
                    severity="warning",
                )
                self.config.pinned_repo = None
                self.config.pinned_org = None
                self._save_config()

        if self.config.pinned_org:
            try:
                await gh("api", f"/orgs/{self.config.pinned_org}")
                self.push_screen(ReposScreen(self.config.pinned_org))
                return
            except GHError:
                self.notify(
                    f"Pinned org {self.config.pinned_org} not found — clearing pin",
                    severity="warning",
                )
                self.config.pinned_org = None
                self._save_config()

        self.push_screen(OrgScreen())

    def _save_config(self) -> None:
        path = self._config_path or DEFAULT_CONFIG_PATH
        save_config(self.config, path)
