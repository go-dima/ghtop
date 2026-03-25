# ghtop/app.py
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from ghtop.config import load_config, save_config, DEFAULT_CONFIG_PATH, Config
from ghtop.gh import gh, gh_raw, GHError

def _setup_logging() -> logging.Logger:
    from datetime import datetime
    import glob
    log_dir = Path("/tmp/ghtop_logs")
    log_dir.mkdir(exist_ok=True)
    # Rotate: keep only 5 most recent, delete older ones
    existing = sorted(glob.glob(str(log_dir / "ghtop_*.log")))
    for old in existing[:-4]:
        Path(old).unlink(missing_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = log_dir / f"ghtop_{ts}.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        force=True,
    )
    logger = logging.getLogger("ghtop")
    logger.info("Log file: %s", log_file)
    return logger

log = _setup_logging()


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

    def on_key(self, event) -> None:
        log.debug("APP on_key: %s | screen=%s | focused=%s",
                  event.key,
                  type(self.screen).__name__,
                  type(self.focused).__name__ if self.focused else None)

    async def on_mount(self) -> None:
        log.debug("GHTopApp on_mount start")
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

        log.debug("auth ok, routing to start")
        await self._route_to_start()

    async def _route_to_start(self) -> None:
        from ghtop.screens.orgs import OrgScreen
        from ghtop.screens.repos import ReposScreen
        from ghtop.screens.prs import PRsScreen

        if self.config.pinned_repo and self.config.pinned_owner:
            try:
                await gh("repo", "view",
                         f"{self.config.pinned_owner}/{self.config.pinned_repo}",
                         "--json", "name")
                # Push full stack so Escape navigates back naturally
                self.push_screen(OrgScreen())
                self.push_screen(ReposScreen(self.config.pinned_owner))
                self.push_screen(PRsScreen(self.config.pinned_owner, self.config.pinned_repo))
                return
            except GHError:
                old_repo = f"{self.config.pinned_owner}/{self.config.pinned_repo}"
                self.config.pinned_repo = None
                self.config.pinned_owner = None
                self._save_config()
                self.push_screen(OrgScreen(
                    message=f"Pinned repo '{old_repo}' not found — pin cleared"
                ))
                return

        if self.config.pinned_owner:
            try:
                await gh("api", f"/users/{self.config.pinned_owner}")
                # Push OrgScreen as base so Escape can go back to it
                self.push_screen(OrgScreen())
                self.push_screen(ReposScreen(self.config.pinned_owner))
                return
            except GHError:
                old = self.config.pinned_owner
                self.config.pinned_owner = None
                self._save_config()
                self.push_screen(OrgScreen(
                    message=f"Pinned owner '{old}' not found — pin cleared"
                ))
                return

        self.push_screen(OrgScreen())

    def _save_config(self) -> None:
        path = self._config_path or DEFAULT_CONFIG_PATH
        save_config(self.config, path)
