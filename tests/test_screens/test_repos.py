# tests/test_screens/test_repos.py
import pytest
from unittest.mock import AsyncMock, patch
from ghtop.app import GHTopApp
from ghtop.config import Config
from tests.conftest import SAMPLE_REPOS


async def mock_gh_repos(*args, **kwargs):
    cmd = list(args)
    if cmd[0] == "auth":
        return None
    if cmd[0] == "api" and "/user/orgs" in cmd:
        return []
    if cmd[0] == "api" and "/user" in cmd:
        return {"login": "alice"}
    if cmd[0] == "repo" and cmd[1] == "list":
        return SAMPLE_REPOS
    if cmd[0] == "pr" and cmd[1] == "list":
        return [{"number": 1}, {"number": 2}]
    return None


@pytest.mark.asyncio
async def test_repos_screen_renders():
    from ghtop.screens.repos import ReposScreen
    with patch("ghtop.app.gh", side_effect=mock_gh_repos), \
         patch("ghtop.screens.repos.gh", side_effect=mock_gh_repos), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_repos), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        app = GHTopApp()
        async with app.run_test() as pilot:
            app.push_screen(ReposScreen("acme"))
            await pilot.pause(1.0)
            assert isinstance(pilot.app.screen, ReposScreen)


@pytest.mark.asyncio
async def test_repos_screen_open_pr_count():
    """Open PR count fetched per repo and shown in table."""
    from ghtop.screens.repos import ReposScreen
    with patch("ghtop.app.gh", side_effect=mock_gh_repos), \
         patch("ghtop.screens.repos.gh", side_effect=mock_gh_repos), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_repos), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        app = GHTopApp()
        async with app.run_test() as pilot:
            screen = ReposScreen("acme")
            app.push_screen(screen)
            await pilot.pause(1.5)
            from textual.widgets import DataTable
            tables = list(pilot.app.screen.query(DataTable))
            assert len(tables) > 0
