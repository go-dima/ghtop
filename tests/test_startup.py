# tests/test_startup.py
from pathlib import Path
import pytest
from unittest.mock import patch
from ghtop.app import GHTopApp, ErrorScreen
from ghtop.gh import GHError
from tests.conftest import SAMPLE_ORGS, SAMPLE_USER


def _app(tmp_path: Path) -> GHTopApp:
    return GHTopApp(config_path=tmp_path / "config.yaml")


async def _mock_gh_ok(*args, **kwargs):
    if list(args)[:2] == ["api", "/user/orgs"]:
        return SAMPLE_ORGS
    if list(args)[:2] == ["api", "/user"]:
        return SAMPLE_USER
    return None


@pytest.mark.asyncio
async def test_startup_gh_not_found(tmp_path):
    """Shows ErrorScreen when gh CLI is not installed."""
    with patch("shutil.which", return_value=None):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.2)
            assert isinstance(pilot.app.screen, ErrorScreen)


@pytest.mark.asyncio
async def test_startup_not_authenticated(tmp_path):
    """Shows ErrorScreen when gh is not authenticated."""
    with patch("ghtop.app.gh_raw", side_effect=GHError("not logged in")), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.2)
            assert isinstance(pilot.app.screen, ErrorScreen)


@pytest.mark.asyncio
async def test_startup_error_screen_q_quits(tmp_path):
    """q key exits from ErrorScreen."""
    with patch("shutil.which", return_value=None):
        async with _app(tmp_path).run_test() as pilot:
            await pilot.pause(0.2)
            assert isinstance(pilot.app.screen, ErrorScreen)
            await pilot.press("q")
            await pilot.pause(0.1)
            assert not pilot.app.is_running


@pytest.mark.asyncio
async def test_startup_pinned_owner_missing_clears_pin(tmp_path):
    """If pinned org no longer exists, pin is cleared and OrgScreen shown."""
    from ghtop.config import Config, save_config
    cfg_path = tmp_path / "config.yaml"
    save_config(Config(pinned_owner="gone-org"), cfg_path)

    async def mock_gh(*args, **kwargs):
        cmd = list(args)
        if cmd[:2] == ["api", "/users/gone-org"]:
            raise GHError("not found")
        if cmd[:2] == ["api", "/user/orgs"]:
            return SAMPLE_ORGS
        if cmd[:2] == ["api", "/user"]:
            return SAMPLE_USER
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with GHTopApp(config_path=cfg_path).run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.screens.orgs import OrgScreen
            assert isinstance(pilot.app.screen, OrgScreen)
            assert pilot.app.config.pinned_owner is None


@pytest.mark.asyncio
async def test_startup_pinned_repo_missing_clears_pin(tmp_path):
    """If pinned repo no longer exists, pin is cleared and OrgScreen shown."""
    from ghtop.config import Config, save_config
    cfg_path = tmp_path / "config.yaml"
    save_config(Config(pinned_owner="acme-corp", pinned_repo="gone-repo"), cfg_path)

    async def mock_gh(*args, **kwargs):
        cmd = list(args)
        if cmd[0] == "repo" and cmd[1] == "view":
            raise GHError("not found")
        if cmd[:2] == ["api", "/user/orgs"]:
            return SAMPLE_ORGS
        if cmd[:2] == ["api", "/user"]:
            return SAMPLE_USER
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.app.gh_raw", return_value=""), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        async with GHTopApp(config_path=cfg_path).run_test() as pilot:
            await pilot.pause(0.5)
            from ghtop.screens.orgs import OrgScreen
            assert isinstance(pilot.app.screen, OrgScreen)
            assert pilot.app.config.pinned_owner is None
            assert pilot.app.config.pinned_repo is None
