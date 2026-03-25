from __future__ import annotations
import asyncio
import json
import logging
from asyncio.subprocess import DEVNULL, PIPE
from typing import Any

from ghtop.config import RATE_LIMIT_BACKOFF

logger = logging.getLogger(__name__)


class GHError(Exception):
    """Raised when `gh` CLI exits with non-zero status."""
    pass


def _is_rate_limit(stderr: str) -> bool:
    lower = stderr.lower()
    return "rate limit" in lower or "429" in lower


async def _run_gh(*args: str) -> bytes:
    """Execute gh CLI with rate-limit backoff. Returns raw stdout bytes.

    Raises GHError on non-zero exit after retries are exhausted.
    """
    delays = list(RATE_LIMIT_BACKOFF)
    attempts = len(delays) + 1

    for attempt in range(attempts):
        proc = await asyncio.create_subprocess_exec(
            "gh", *args,
            stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return stdout

        err = stderr.decode(errors="replace")

        if _is_rate_limit(err) and attempt < len(delays):
            delay = delays[attempt]
            logger.warning("Rate limited by GitHub, retrying in %ss", delay)
            await asyncio.sleep(delay)
            continue

        raise GHError(err)

    raise GHError("Rate limit retries exhausted")


async def gh(*args: str) -> Any:
    """Run `gh <args>` and return parsed JSON, or None for empty output.

    Raises GHError on non-zero exit (after rate-limit retries are exhausted).
    """
    stdout = await _run_gh(*args)
    text = stdout.strip()
    return json.loads(text) if text else None


async def gh_raw(*args: str) -> str:
    """Run `gh <args>` and return raw stdout string (no JSON parsing).

    Used for `gh run view --log` which returns tab-delimited text.
    Raises GHError on non-zero exit.
    """
    stdout = await _run_gh(*args)
    return stdout.decode(errors="replace")
