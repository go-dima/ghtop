# tests/test_screens/test_prs.py
import pytest
from unittest.mock import AsyncMock, patch
from ghtop.app import GHTopApp
from ghtop.config import Config
from tests.conftest import SAMPLE_PRS


SAMPLE_RUNS = [
    {
        "databaseId": 1001,
        "name": "CI",
        "status": "completed",
        "conclusion": "success",
        "startedAt": "2026-03-19T10:00:00Z",
        "updatedAt": "2026-03-19T10:05:00Z",
    }
]


async def mock_gh_prs(*args, **kwargs):
    cmd = list(args)
    if cmd[0] == "auth":
        return None
    if "--author" in cmd:
        return [SAMPLE_PRS[0]]
    if "--search" in cmd:
        return [SAMPLE_PRS[1]]
    if cmd[0] == "run" and cmd[1] == "list":
        return SAMPLE_RUNS
    return []


@pytest.mark.asyncio
async def test_prs_screen_filter_mine_default():
    """filter_mine starts as True."""
    from ghtop.screens.prs import PRsScreen
    screen = PRsScreen("acme", "backend-api")
    assert screen._filter_mine is True


@pytest.mark.asyncio
async def test_prs_screen_renders():
    from ghtop.screens.prs import PRsScreen
    with patch("ghtop.app.gh", side_effect=mock_gh_prs), \
         patch("ghtop.screens.prs.gh", side_effect=mock_gh_prs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_prs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        app = GHTopApp()
        async with app.run_test() as pilot:
            from ghtop.screens.prs import PRsScreen
            app.push_screen(PRsScreen("acme", "backend-api"))
            await pilot.pause(1.5)
            assert isinstance(pilot.app.screen, PRsScreen)


@pytest.mark.asyncio
async def test_prs_screen_toggle_filter():
    """m key toggles filter_mine."""
    from ghtop.screens.prs import PRsScreen
    with patch("ghtop.app.gh", side_effect=mock_gh_prs), \
         patch("ghtop.screens.prs.gh", side_effect=mock_gh_prs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_prs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        app = GHTopApp()
        async with app.run_test() as pilot:
            screen = PRsScreen("acme", "backend-api")
            app.push_screen(screen)
            await pilot.pause(0.5)
            assert screen._filter_mine is True
            await pilot.press("m")
            await pilot.pause(0.3)
            assert screen._filter_mine is False


def test_derive_pr_status_in_progress():
    from ghtop.screens.prs import derive_pr_status
    jobs = [{"status": "in_progress", "conclusion": None}]
    assert derive_pr_status(jobs) == "in_progress"


def test_derive_pr_status_failure():
    from ghtop.screens.prs import derive_pr_status
    jobs = [
        {"status": "completed", "conclusion": "success"},
        {"status": "completed", "conclusion": "failure"},
    ]
    assert derive_pr_status(jobs) == "failure"


def test_derive_pr_status_all_success():
    from ghtop.screens.prs import derive_pr_status
    jobs = [
        {"status": "completed", "conclusion": "success"},
        {"status": "completed", "conclusion": "success"},
    ]
    assert derive_pr_status(jobs) == "success"
