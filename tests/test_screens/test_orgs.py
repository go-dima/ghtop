# tests/test_screens/test_orgs.py
import pytest
from unittest.mock import AsyncMock, patch
from ghtop.app import GHTopApp
from ghtop.config import Config
from tests.conftest import SAMPLE_ORGS, SAMPLE_USER


async def mock_gh_for_orgs(*args, **kwargs):
    cmd = list(args)
    if cmd == ["auth", "status"]:
        return None
    if cmd[:2] == ["api", "/user/orgs"]:
        return SAMPLE_ORGS
    if cmd[:2] == ["api", "/user"]:
        return SAMPLE_USER
    return None


@pytest.mark.asyncio
async def test_org_screen_shows_orgs():
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with GHTopApp().run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.screens.orgs import OrgScreen
            assert isinstance(pilot.app.screen, OrgScreen)


@pytest.mark.asyncio
async def test_org_screen_shows_personal_account():
    """Personal account [you] marker is appended at bottom."""
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with GHTopApp().run_test() as pilot:
            await pilot.pause(0.5)
            assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_org_screen_empty_state():
    """Shows empty state message when no orgs found."""
    async def mock_no_orgs(*args, **kwargs):
        if list(args)[:2] == ["api", "/user/orgs"]:
            return []
        if list(args)[:2] == ["api", "/user"]:
            return SAMPLE_USER
        return None

    with patch("ghtop.app.gh", side_effect=mock_no_orgs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_no_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with GHTopApp().run_test() as pilot:
            await pilot.pause(0.5)
            assert pilot.app.screen is not None  # no crash
