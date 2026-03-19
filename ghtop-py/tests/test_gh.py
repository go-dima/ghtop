import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from ghtop.gh import gh, GHError


def make_proc(returncode=0, stdout=b'{"ok": true}', stderr=b''):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_gh_success_returns_parsed_json():
    proc = make_proc(stdout=b'{"login": "alice"}')
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await gh("api", "/user")
    assert result == {"login": "alice"}


@pytest.mark.asyncio
async def test_gh_empty_stdout_returns_none():
    proc = make_proc(stdout=b'')
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await gh("run", "rerun", "123", "--failed")
    assert result is None


@pytest.mark.asyncio
async def test_gh_nonzero_exit_raises_gherror():
    proc = make_proc(returncode=1, stdout=b'', stderr=b'error: not found')
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(GHError) as exc_info:
            await gh("pr", "list")
    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gh_rate_limit_retries_with_backoff():
    rate_limit_proc = make_proc(returncode=1, stderr=b'rate limit exceeded')
    success_proc = make_proc(stdout=b'[]')
    call_count = 0

    async def fake_exec(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return rate_limit_proc if call_count < 3 else success_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await gh("pr", "list")

    assert result == []
    assert call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(2)
    mock_sleep.assert_any_call(4)


@pytest.mark.asyncio
async def test_gh_rate_limit_exhausted_raises():
    proc = make_proc(returncode=1, stderr=b'rate limit exceeded')
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(GHError) as exc_info:
                await gh("pr", "list")
    assert "rate limit" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_gh_list_response():
    proc = make_proc(stdout=b'[{"number": 1}, {"number": 2}]')
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await gh("pr", "list", "--json", "number")
    assert result == [{"number": 1}, {"number": 2}]


@pytest.mark.asyncio
async def test_gh_raw_returns_text():
    from ghtop.gh import gh_raw
    proc = make_proc(stdout=b"build\tstep1\tlog line\n")
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await gh_raw("run", "view", "123", "--log")
    assert result == "build\tstep1\tlog line\n"
