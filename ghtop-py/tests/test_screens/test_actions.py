# tests/test_screens/test_actions.py
import pytest
from unittest.mock import AsyncMock, patch


def test_double_tap_state_machine():
    """_pending_rerun flag is managed correctly."""
    from ghtop.screens.actions import ActionsScreen
    screen = ActionsScreen(
        org="acme", repo="api",
        pr={"number": 42, "title": "fix", "author": {"login": "alice"},
            "createdAt": "2026-03-19T10:00:00Z", "labels": [],
            "reviewRequests": [], "_runs": [], "headRefName": "fix/auth"}
    )
    assert screen._pending_rerun is False
    assert screen._pending_rerun_timer is None


@pytest.mark.asyncio
async def test_actions_screen_renders():
    from ghtop.screens.actions import ActionsScreen
    from ghtop.app import GHTopApp

    sample_pr = {
        "number": 42, "title": "fix: auth", "author": {"login": "alice"},
        "createdAt": "2026-03-19T10:00:00Z", "labels": [{"name": "bug"}],
        "reviewRequests": [{"requestedReviewer": {"login": "bob"}}],
        "_runs": [{"databaseId": 1001, "name": "CI", "status": "completed",
                   "conclusion": "success", "startedAt": "2026-03-19T10:00:00Z",
                   "updatedAt": "2026-03-19T10:05:00Z"}],
        "headRefName": "fix/auth",
    }

    async def mock_gh(*args, **kwargs):
        cmd = list(args)
        if cmd[0] == "auth":
            return None
        if cmd[0] == "run" and cmd[1] == "view":
            return {"jobs": [
                {"name": "build", "status": "completed", "conclusion": "success",
                 "startedAt": "2026-03-19T10:00:00Z",
                 "completedAt": "2026-03-19T10:01:00Z",
                 "workflowName": "CI",
                 "steps": []}
            ]}
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.screens.actions.gh", side_effect=mock_gh), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        app = GHTopApp()
        async with app.run_test() as pilot:
            app.push_screen(ActionsScreen(org="acme", repo="api", pr=sample_pr))
            await pilot.pause(1.0)
            assert isinstance(pilot.app.screen, ActionsScreen)
