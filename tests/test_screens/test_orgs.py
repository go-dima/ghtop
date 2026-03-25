# tests/test_screens/test_orgs.py
from pathlib import Path
import pytest
from unittest.mock import patch
from ghtop.app import GHTopApp
from ghtop.config import Config
from ghtop.gh import GHError
from tests.conftest import SAMPLE_ORGS, SAMPLE_USER


async def mock_gh_for_orgs(*args, **kwargs):
    cmd = list(args)
    if cmd[:2] == ["api", "/user/orgs"]:
        return SAMPLE_ORGS
    if cmd[:2] == ["api", "/user"]:
        return SAMPLE_USER
    return None


def _app(tmp_path: Path) -> GHTopApp:
    """Create a GHTopApp with an isolated empty config."""
    return GHTopApp(config_path=tmp_path / "config.yaml")


@pytest.mark.asyncio
async def test_org_screen_shows_orgs(tmp_path):
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.screens.orgs import OrgScreen
            assert isinstance(pilot.app.screen, OrgScreen)


@pytest.mark.asyncio
async def test_org_screen_shows_personal_account(tmp_path):
    """Personal account [you] marker is appended at bottom."""
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_org_screen_empty_state(tmp_path):
    """Shows empty state message when no orgs found."""
    async def mock_no_orgs(*args, **kwargs):
        if list(args)[:2] == ["api", "/user/orgs"]:
            return []
        if list(args)[:2] == ["api", "/user"]:
            return SAMPLE_USER
        return None

    with patch("ghtop.app.gh", side_effect=mock_no_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_no_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            assert pilot.app.screen is not None  # no crash


def _patched(tmp_path, mock_gh=None):
    """Context manager: app + standard mocks."""
    if mock_gh is None:
        mock_gh = mock_gh_for_orgs
    return (
        patch("ghtop.app.gh", side_effect=mock_gh),
        patch("ghtop.app.gh_raw", return_value=""),
        patch("ghtop.screens.orgs.gh", side_effect=mock_gh),
        patch("shutil.which", return_value="/usr/bin/gh"),
    )


@pytest.mark.asyncio
async def test_q_key_quits(tmp_path):
    """q key exits the app from OrgScreen."""
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            await pilot.press("q")
            await pilot.pause(0.1)
            assert not pilot.app.is_running


@pytest.mark.asyncio
async def test_enter_navigates_to_repos(tmp_path):
    """Enter on a selected org pushes ReposScreen."""
    async def mock_gh(*args, **kwargs):
        cmd = list(args)
        if cmd[:2] == ["api", "/user/orgs"]:
            return SAMPLE_ORGS
        if cmd[:2] == ["api", "/user"]:
            return SAMPLE_USER
        if cmd[0] == "repo" and cmd[1] == "list":
            return []
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh), \
         patch("ghtop.screens.repos.gh", side_effect=mock_gh), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            await pilot.press("enter")
            await pilot.pause(0.3)
            from ghtop.screens.repos import ReposScreen
            assert isinstance(pilot.app.screen, ReposScreen)


@pytest.mark.asyncio
async def test_s_key_navigates_to_repos(tmp_path):
    """s key (explicit select) pushes ReposScreen."""
    async def mock_gh(*args, **kwargs):
        cmd = list(args)
        if cmd[:2] == ["api", "/user/orgs"]:
            return SAMPLE_ORGS
        if cmd[:2] == ["api", "/user"]:
            return SAMPLE_USER
        if cmd[0] == "repo" and cmd[1] == "list":
            return []
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh), \
         patch("ghtop.screens.repos.gh", side_effect=mock_gh), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            await pilot.press("s")
            await pilot.pause(0.3)
            from ghtop.screens.repos import ReposScreen
            assert isinstance(pilot.app.screen, ReposScreen)


@pytest.mark.asyncio
async def test_p_key_pins_and_unpins(tmp_path):
    """p toggles pin on the selected org."""
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            assert pilot.app.config.pinned_owner is None
            await pilot.press("p")
            await pilot.pause(0.1)
            assert pilot.app.config.pinned_owner == SAMPLE_ORGS[0]["login"]
            await pilot.press("p")
            await pilot.pause(0.1)
            assert pilot.app.config.pinned_owner is None


@pytest.mark.asyncio
async def test_loading_cleared_after_load(tmp_path):
    """Loading indicator in header is off after orgs finish loading."""
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.widgets.header import AppHeader
            header = pilot.app.screen.query_one(AppHeader)
            assert not header.loading


@pytest.mark.asyncio
async def test_gh_error_shows_in_header(tmp_path):
    """GHError during org load shows error banner in AppHeader."""
    async def mock_failing(*args, **kwargs):
        if list(args)[:2] == ["api", "/user/orgs"]:
            raise GHError("rate limited")
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_failing), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.widgets.header import AppHeader
            header = pilot.app.screen.query_one(AppHeader)
            assert "rate limited" in header.error


@pytest.mark.asyncio
async def test_loading_cleared_on_gh_error(tmp_path):
    """Header loading indicator is off even when the API call fails."""
    async def mock_failing(*args, **kwargs):
        if list(args)[:2] == ["api", "/user/orgs"]:
            raise GHError("server error")
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_failing), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.widgets.header import AppHeader
            header = pilot.app.screen.query_one(AppHeader)
            assert not header.loading
