import pytest
from ghtop.screens.logs import filter_log_lines


def test_filter_log_lines_by_job_name():
    raw = (
        "build\tstep1\tSetting up Node.js 20\n"
        "lint\tstep1\tRunning ESLint\n"
        "build\tstep2\tnpm ci started\n"
        "test\tstep1\tRunning tests\n"
    )
    result = filter_log_lines(raw, "build")
    assert result == ["Setting up Node.js 20", "npm ci started"]


def test_filter_log_lines_exact_match():
    """Only exact job name match on first tab-delimited field."""
    raw = "build-and-test\tstep1\tsome log\nbuild\tstep1\tother log\n"
    result = filter_log_lines(raw, "build")
    assert result == ["other log"]


def test_filter_log_lines_empty():
    result = filter_log_lines("", "build")
    assert result == []


def test_filter_log_lines_no_match():
    raw = "lint\tstep1\tRunning ESLint\n"
    result = filter_log_lines(raw, "build")
    assert result == []


@pytest.mark.asyncio
async def test_logs_screen_renders():
    from ghtop.screens.logs import LogsScreen
    from ghtop.app import GHTopApp
    from unittest.mock import patch

    fake_log = "build\tstep1\tSetting up Node.js\nbuild\tstep2\tnpm ci done\n"

    async def mock_gh(*args, **kwargs):
        cmd = list(args)
        if cmd[0] == "auth":
            return None
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh), \
         patch("ghtop.screens.logs.gh_raw", return_value=fake_log), \
         patch("shutil.which", return_value="/usr/bin/gh"):
        app = GHTopApp()
        async with app.run_test() as pilot:
            app.push_screen(LogsScreen(
                run_id=1001, repo="acme/api", job_name="build",
                pr_number=42, workflow_name="CI"
            ))
            await pilot.pause(0.8)
            assert isinstance(pilot.app.screen, LogsScreen)
