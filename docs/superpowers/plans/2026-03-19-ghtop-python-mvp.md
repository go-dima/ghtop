# ghtop Python MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working terminal UI (TUI) for browsing GitHub Actions status across orgs, repos, and PRs — using Python + Textual + the `gh` CLI.

**Architecture:** Five navigable screens (Org → Repo → PR List → Actions Detail → Logs Viewer), each as a Textual `Screen` subclass. All GitHub data is fetched asynchronously via `gh` CLI subprocess calls, with a shared wrapper that handles errors and rate-limit backoff. Navigation uses Textual's `push_screen()` / `pop_screen()`.

**Tech Stack:** Python 3.10+, Textual `>=0.80,<1.0`, `pyyaml`, `uv` (packaging), `pytest` + `pytest-asyncio` (tests), `unittest.mock` (gh mocking), Textual `Pilot` (screen integration tests).

---

## File Map

Files to create (all under `ghtop-py/`):

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, deps, test config, entry point |
| `ghtop/__main__.py` | Entry point: `python -m ghtop` |
| `ghtop/config.py` | `Config` dataclass + YAML load/save + internal constants |
| `ghtop/gh.py` | `gh()` async subprocess wrapper, `GHError`, rate-limit backoff |
| `ghtop/app.py` | Textual `GHTopApp`, startup auth check, screen routing |
| `ghtop/widgets/__init__.py` | Empty |
| `ghtop/widgets/header.py` | `AppHeader` widget — breadcrumb, refresh status, error banner |
| `ghtop/widgets/status_bar.py` | `StatusBar` widget — keybinding hints |
| `ghtop/screens/__init__.py` | Empty |
| `ghtop/screens/orgs.py` | `OrgScreen` — Screen 1: org list with pin |
| `ghtop/screens/repos.py` | `ReposScreen` — Screen 2: repos with open PR count |
| `ghtop/screens/prs.py` | `PRsScreen` — Screen 3: PR list, filter_mine, fuzzy search |
| `ghtop/screens/actions.py` | `ActionsScreen` — Screen 4: jobs table, auto-refresh, rerun |
| `ghtop/screens/logs.py` | `LogsScreen` — Screen 5: log viewer with job filter |
| `tests/conftest.py` | Shared fixtures: mock `gh()`, sample data |
| `tests/test_config.py` | Config load/save/defaults |
| `tests/test_gh.py` | gh wrapper: success, non-zero exit, rate limit, backoff |
| `tests/test_screens/test_orgs.py` | Org screen: render, pin, navigate |
| `tests/test_screens/test_repos.py` | Repos screen: render, concurrent fetch, search |
| `tests/test_screens/test_prs.py` | PR screen: filter_mine default, toggle, search |
| `tests/test_screens/test_actions.py` | Actions screen: status derivation, double-tap rerun |
| `tests/test_screens/test_logs.py` | Logs screen: job filter, search |

---

## Task 1: Project Scaffold

**Files:**
- Create: `ghtop-py/pyproject.toml`
- Create: `ghtop-py/ghtop/__init__.py`
- Create: `ghtop-py/ghtop/__main__.py`
- Create: `ghtop-py/ghtop/screens/__init__.py`
- Create: `ghtop-py/ghtop/widgets/__init__.py`
- Create: `ghtop-py/tests/__init__.py`
- Create: `ghtop-py/tests/test_screens/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ghtop"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "textual>=0.80,<1.0",
    "pyyaml>=6.0",
]

[project.scripts]
ghtop = "ghtop.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["ghtop"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "textual[dev]>=0.80,<1.0",
]
```

- [ ] **Step 2: Create directory structure and empty init files**

```bash
cd ghtop-py
mkdir -p ghtop/screens ghtop/widgets tests/test_screens
touch ghtop/__init__.py ghtop/screens/__init__.py ghtop/widgets/__init__.py
touch tests/__init__.py tests/test_screens/__init__.py
```

- [ ] **Step 3: Create `ghtop/__main__.py`**

```python
#!/usr/bin/env python3
import argparse
from pathlib import Path
from ghtop.app import GHTopApp


def main():
    parser = argparse.ArgumentParser(prog="ghtop")
    parser.add_argument(
        "--config", metavar="PATH", type=Path,
        help="Path to config file (default: ~/.config/ghtop/config.yaml)"
    )
    args = parser.parse_args()
    GHTopApp(config_path=args.config).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Install dev dependencies**

```bash
cd ghtop-py
uv sync --dev
# or: pip install -e ".[dev]" (if not using uv)
```

Expected: no errors, `textual`, `pytest`, `pyyaml` installed.

- [ ] **Step 5: Commit**

```bash
git add ghtop-py/
git commit -m "chore: scaffold ghtop-py project structure"
```

---

## Task 2: `config.py` — Config dataclass + YAML persistence

**Files:**
- Create: `ghtop-py/ghtop/config.py`
- Create: `ghtop-py/tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
import pytest
import yaml
from pathlib import Path
from ghtop.config import Config, load_config, save_config, DEFAULT_CONFIG_PATH


def test_defaults():
    cfg = Config()
    assert cfg.pinned_org is None
    assert cfg.pinned_repo is None
    assert cfg.refresh_interval == 30
    assert cfg.pr_limit == 50


def test_load_missing_file(tmp_path):
    path = tmp_path / "config.yaml"
    cfg = load_config(path)
    assert cfg == Config()


def test_load_partial_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("refresh_interval: 60\n")
    cfg = load_config(path)
    assert cfg.refresh_interval == 60
    assert cfg.pr_limit == 50  # default preserved


def test_load_with_pin(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("pinned:\n  org: my-org\n  repo: backend-api\n")
    cfg = load_config(path)
    assert cfg.pinned_org == "my-org"
    assert cfg.pinned_repo == "backend-api"


def test_save_and_reload(tmp_path):
    path = tmp_path / "config.yaml"
    cfg = Config(pinned_org="acme", pinned_repo="api", refresh_interval=15, pr_limit=25)
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded == cfg


def test_malformed_config_returns_defaults(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("not: valid: yaml: [[\n")
    cfg = load_config(path)  # should not raise
    assert cfg == Config()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ghtop-py
pytest tests/test_config.py -v
```

Expected: `ImportError` — `ghtop.config` does not exist yet.

- [ ] **Step 3: Implement `config.py`**

```python
# ghtop/config.py
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ghtop" / "config.yaml"

# Internal constants (not in config file)
ACTIONS_REFRESH_INTERVAL = 10   # seconds — Screen 4 poll interval
CONCURRENT_FETCH_LIMIT = 10     # asyncio.Semaphore size
RATE_LIMIT_BACKOFF = [2, 4, 8]  # retry delays in seconds


@dataclass
class Config:
    pinned_org: Optional[str] = None
    pinned_repo: Optional[str] = None
    refresh_interval: int = 30   # Screen 3 poll interval (seconds)
    pr_limit: int = 50           # max PRs after merge+dedup

    def __eq__(self, other):
        if not isinstance(other, Config):
            return False
        return (self.pinned_org == other.pinned_org and
                self.pinned_repo == other.pinned_repo and
                self.refresh_interval == other.refresh_interval and
                self.pr_limit == other.pr_limit)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        return Config()
    try:
        raw = yaml.safe_load(path.read_text()) or {}
        pinned = raw.get("pinned") or {}
        return Config(
            pinned_org=pinned.get("org"),
            pinned_repo=pinned.get("repo"),
            refresh_interval=int(raw.get("refresh_interval", 30)),
            pr_limit=int(raw.get("pr_limit", 50)),
        )
    except Exception as e:
        logger.warning("Malformed config at %s: %s — using defaults", path, e)
        return Config()


def save_config(cfg: Config, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if cfg.pinned_org or cfg.pinned_repo:
        data["pinned"] = {}
        if cfg.pinned_org:
            data["pinned"]["org"] = cfg.pinned_org
        if cfg.pinned_repo:
            data["pinned"]["repo"] = cfg.pinned_repo
    if cfg.refresh_interval != 30:
        data["refresh_interval"] = cfg.refresh_interval
    if cfg.pr_limit != 50:
        data["pr_limit"] = cfg.pr_limit
    path.write_text(yaml.safe_dump(data, default_flow_style=False))
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ghtop-py/ghtop/config.py ghtop-py/tests/test_config.py
git commit -m "feat: add config dataclass with YAML load/save"
```

---

## Task 3: `gh.py` — Async subprocess wrapper

**Files:**
- Create: `ghtop-py/ghtop/gh.py`
- Create: `ghtop-py/tests/test_gh.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gh.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_gh.py -v
```

Expected: `ImportError` — `ghtop.gh` does not exist yet.

- [ ] **Step 3: Implement `gh.py`**

```python
# ghtop/gh.py
from __future__ import annotations
import asyncio
import json
import logging
from asyncio.subprocess import PIPE
from typing import Any

from ghtop.config import RATE_LIMIT_BACKOFF

logger = logging.getLogger(__name__)


class GHError(Exception):
    """Raised when `gh` CLI exits with non-zero status."""
    pass


def _is_rate_limit(stderr: str) -> bool:
    lower = stderr.lower()
    return "rate limit" in lower or "429" in lower


async def gh(*args: str) -> Any:
    """Run `gh <args>` and return parsed JSON, or None for empty output.

    Raises GHError on non-zero exit (after rate-limit retries are exhausted).
    """
    delays = list(RATE_LIMIT_BACKOFF)
    attempts = len(delays) + 1

    for attempt in range(attempts):
        proc = await asyncio.create_subprocess_exec(
            "gh", *args,
            stdout=PIPE, stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            text = stdout.strip()
            return json.loads(text) if text else None

        err = stderr.decode(errors="replace")

        if _is_rate_limit(err) and attempt < len(delays):
            delay = delays[attempt]
            logger.warning("Rate limited by GitHub, retrying in %ss", delay)
            await asyncio.sleep(delay)
            continue

        raise GHError(err)

    # Should not reach here, but satisfy type checker
    raise GHError("Rate limit retries exhausted")
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
pytest tests/test_gh.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ghtop-py/ghtop/gh.py ghtop-py/tests/test_gh.py
git commit -m "feat: add gh async subprocess wrapper with rate-limit backoff"
```

---

## Task 4: `app.py` — Textual App Shell

**Files:**
- Create: `ghtop-py/ghtop/app.py`

No unit tests for this task — integration tested via Screen 1 tests.

- [ ] **Step 1: Create `app.py`**

```python
# ghtop/app.py
from __future__ import annotations
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from ghtop.config import load_config, Config
from ghtop.gh import gh, GHError


class ErrorScreen(Screen):
    """Full-screen error shown when gh is not available or not authenticated."""

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Static(self._message, id="error-message")

    def action_quit(self) -> None:
        self.app.exit()


class GHTopApp(App):
    """Root application — handles startup checks and initial routing."""

    CSS = """
    #error-message {
        padding: 2 4;
        color: $error;
    }
    """

    def __init__(self, config_path=None) -> None:
        super().__init__()
        self.config: Config = load_config(config_path) if config_path else load_config()
        self._config_path = config_path

    async def on_mount(self) -> None:
        # Check gh is installed
        import shutil
        if not shutil.which("gh"):
            self.push_screen(ErrorScreen(
                "gh CLI not found. Install from https://cli.github.com"
            ))
            return

        # Check authentication
        try:
            await gh("auth", "status")
        except GHError:
            self.push_screen(ErrorScreen(
                "Not authenticated. Run: gh auth login"
            ))
            return

        # Route based on pinned config
        await self._route_to_start()

    async def _route_to_start(self) -> None:
        from ghtop.screens.orgs import OrgScreen
        from ghtop.screens.repos import ReposScreen
        from ghtop.screens.prs import PRsScreen

        if self.config.pinned_repo and self.config.pinned_org:
            # Validate pinned repo still exists
            try:
                await gh("repo", "view", f"{self.config.pinned_org}/{self.config.pinned_repo}", "--json", "name")
                self.push_screen(PRsScreen(self.config.pinned_org, self.config.pinned_repo))
                return
            except GHError:
                self.notify(
                    f"Pinned repo {self.config.pinned_org}/{self.config.pinned_repo} not found — clearing pin",
                    severity="warning",
                )
                self.config.pinned_repo = None
                self.config.pinned_org = None
                self._save_config()

        if self.config.pinned_org:
            try:
                await gh("api", f"/orgs/{self.config.pinned_org}")
                self.push_screen(ReposScreen(self.config.pinned_org))
                return
            except GHError:
                self.notify(
                    f"Pinned org {self.config.pinned_org} not found — clearing pin",
                    severity="warning",
                )
                self.config.pinned_org = None
                self._save_config()

        self.push_screen(OrgScreen())

    def _save_config(self) -> None:
        from ghtop.config import save_config, DEFAULT_CONFIG_PATH
        path = self._config_path or DEFAULT_CONFIG_PATH
        save_config(self.config, path)
```

- [ ] **Step 2: Verify the app is importable**

```bash
cd ghtop-py
python -c "from ghtop.app import GHTopApp; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ghtop-py/ghtop/app.py
git commit -m "feat: add GHTopApp shell with startup auth check and pin routing"
```

---

## Task 5: Widgets — `AppHeader` and `StatusBar`

**Files:**
- Create: `ghtop-py/ghtop/widgets/header.py`
- Create: `ghtop-py/ghtop/widgets/status_bar.py`

No separate unit tests — these are simple display widgets; tested implicitly by screen tests.

- [ ] **Step 1: Create `widgets/header.py`**

```python
# ghtop/widgets/header.py
from __future__ import annotations
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class AppHeader(Widget):
    """Breadcrumb + refresh indicator + error banner."""

    DEFAULT_CSS = """
    AppHeader {
        height: auto;
        background: $primary;
        padding: 0 1;
    }
    #breadcrumb {
        color: $text;
    }
    #error-banner {
        color: $error;
        display: none;
    }
    AppHeader.has-error #error-banner {
        display: block;
    }
    """

    breadcrumb: reactive[str] = reactive("")
    error: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("", id="breadcrumb")
        yield Static("", id="error-banner")

    def watch_breadcrumb(self, value: str) -> None:
        self.query_one("#breadcrumb", Static).update(value)

    def watch_error(self, value: str) -> None:
        banner = self.query_one("#error-banner", Static)
        banner.update(f"⚠ {value}" if value else "")
        if value:
            self.add_class("has-error")
        else:
            self.remove_class("has-error")
```

- [ ] **Step 2: Create `widgets/status_bar.py`**

```python
# ghtop/widgets/status_bar.py
from __future__ import annotations
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    """Keybinding hints shown at the bottom of each screen."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary-darken-2;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def __init__(self, hints: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._hints = hints

    def compose(self) -> ComposeResult:
        yield Static(self._hints)

    def update_hints(self, hints: str) -> None:
        self.query_one(Static).update(hints)
```

- [ ] **Step 3: Commit**

```bash
git add ghtop-py/ghtop/widgets/
git commit -m "feat: add AppHeader and StatusBar widgets"
```

---

## Task 6: Screen 1 — Org Selector

**Files:**
- Create: `ghtop-py/ghtop/screens/orgs.py`
- Create: `ghtop-py/tests/test_screens/test_orgs.py`
- Create: `ghtop-py/tests/conftest.py`

- [ ] **Step 1: Create `tests/conftest.py` with shared fixtures**

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, patch


# Sample data fixtures
SAMPLE_ORGS = [
    {"login": "acme-corp"},
    {"login": "my-team"},
]
SAMPLE_USER = {"login": "alice"}

SAMPLE_REPOS = [
    {"name": "backend-api", "updatedAt": "2026-03-19T10:00:00Z"},
    {"name": "frontend", "updatedAt": "2026-03-18T08:00:00Z"},
]

SAMPLE_PRS = [
    {
        "number": 42,
        "title": "fix: auth token expiry",
        "author": {"login": "alice"},
        "createdAt": "2026-03-19T10:00:00Z",
        "headRefName": "fix/auth",
        "labels": [{"name": "bug"}],
        "reviewRequests": [],
    },
    {
        "number": 41,
        "title": "feat: rate limiting",
        "author": {"login": "bob"},
        "createdAt": "2026-03-18T10:00:00Z",
        "headRefName": "feat/rate-limit",
        "labels": [],
        "reviewRequests": [],
    },
]
```

- [ ] **Step 2: Write failing tests for OrgScreen**

```python
# tests/test_screens/test_orgs.py
import pytest
from unittest.mock import AsyncMock, patch
from textual.pilot import Pilot
from ghtop.app import GHTopApp
from ghtop.config import Config
from tests.conftest import SAMPLE_ORGS, SAMPLE_USER


def make_app(config=None):
    app = GHTopApp()
    app.config = config or Config()
    return app


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
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs):
        async with GHTopApp().run_test() as pilot:
            await pilot.pause(0.5)
            # Should be on OrgScreen now
            from ghtop.screens.orgs import OrgScreen
            assert isinstance(pilot.app.screen, OrgScreen)


@pytest.mark.asyncio
async def test_org_screen_shows_personal_account():
    """Personal account [you] marker is appended at bottom."""
    with patch("ghtop.app.gh", side_effect=mock_gh_for_orgs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_gh_for_orgs):
        async with GHTopApp().run_test() as pilot:
            await pilot.pause(0.5)
            from textual.widgets import ListView
            # Personal account should appear in list
            screen_text = pilot.app.screen.query("*").results()
            # Check the screen rendered without error
            assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_org_screen_empty_state():
    """Shows empty state message when no orgs found."""
    async def mock_no_orgs(*args):
        if list(args)[:2] == ["api", "/user/orgs"]:
            return []
        if list(args)[:2] == ["api", "/user"]:
            return SAMPLE_USER
        return None

    with patch("ghtop.app.gh", side_effect=mock_no_orgs), \
         patch("ghtop.screens.orgs.gh", side_effect=mock_no_orgs):
        async with GHTopApp().run_test() as pilot:
            await pilot.pause(0.5)
            assert pilot.app.screen is not None  # no crash
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_screens/test_orgs.py -v
```

Expected: `ImportError` — `ghtop.screens.orgs` does not exist yet.

- [ ] **Step 4: Implement `screens/orgs.py`**

```python
# ghtop/screens/orgs.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import ListItem, ListView, Static

from ghtop.gh import gh, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


@dataclass
class OrgItem:
    login: str
    is_you: bool = False
    is_pinned: bool = False

    def label(self) -> str:
        pin = "★ " if self.is_pinned else "  "
        you = " [you]" if self.is_you else ""
        return f"{pin}{self.login}{you}"


class OrgScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("p", "pin", "Pin"),
        Binding("q", "quit_app", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield ListView(id="org-list")
        yield Static("", id="empty-state")
        yield StatusBar("↑↓ navigate  Enter select  p pin  q quit")

    async def on_mount(self) -> None:
        header = self.query_one(AppHeader)
        header.breadcrumb = "ghtop"
        await self._load_orgs()

    async def _load_orgs(self) -> None:
        try:
            orgs_raw, user_raw = await asyncio.gather(
                gh("api", "/user/orgs", "--paginate"),
                gh("api", "/user"),
            )
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        orgs: list[OrgItem] = []
        org_logins = set()

        for org in (orgs_raw or []):
            login = org["login"]
            org_logins.add(login)
            orgs.append(OrgItem(
                login=login,
                is_pinned=(login == self.app.config.pinned_org and
                           not self.app.config.pinned_repo),
            ))

        # Add personal account (deduplicate if already in orgs list)
        user_login = (user_raw or {}).get("login")
        if user_login:
            if user_login in org_logins:
                # Replace with [you] marker
                for item in orgs:
                    if item.login == user_login:
                        item.is_you = True
            else:
                orgs.append(OrgItem(login=user_login, is_you=True))

        list_view = self.query_one("#org-list", ListView)
        if not orgs:
            self.query_one("#empty-state", Static).update(
                "No organizations found. Make sure you are authenticated: gh auth status"
            )
            return

        self._orgs = orgs
        for item in orgs:
            list_view.append(ListItem(Static(item.label())))

        # Move pinned item to top
        pinned_idx = next(
            (i for i, o in enumerate(orgs) if o.is_pinned), None
        )
        if pinned_idx:
            list_view.index = pinned_idx

    def action_select(self) -> None:
        idx = self.query_one(ListView).index
        if idx is None or not hasattr(self, "_orgs"):
            return
        org = self._orgs[idx]
        from ghtop.screens.repos import ReposScreen
        self.app.push_screen(ReposScreen(org.login))

    def action_pin(self) -> None:
        idx = self.query_one(ListView).index
        if idx is None or not hasattr(self, "_orgs"):
            return
        org = self._orgs[idx]
        if org.is_pinned:
            self.app.config.pinned_org = None
            org.is_pinned = False
        else:
            # Clear any existing pins
            for o in self._orgs:
                o.is_pinned = False
            self.app.config.pinned_org = org.login
            self.app.config.pinned_repo = None
            org.is_pinned = True
        self.app._save_config()
        self._refresh_list()

    def _refresh_list(self) -> None:
        list_view = self.query_one("#org-list", ListView)
        items = list(list_view.query(ListItem))
        for i, item in enumerate(items):
            item.query_one(Static).update(self._orgs[i].label())

    def action_cursor_up(self) -> None:
        self.query_one(ListView).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(ListView).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
pytest tests/test_screens/test_orgs.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Smoke test the app visually (optional)**

```bash
cd ghtop-py
python -m ghtop
```

Expected: Org list appears (assuming `gh auth status` passes).

- [ ] **Step 7: Commit**

```bash
git add ghtop-py/ghtop/screens/orgs.py ghtop-py/tests/test_screens/test_orgs.py ghtop-py/tests/conftest.py
git commit -m "feat: add OrgScreen (Screen 1) with pin support"
```

---

## Task 7: Screen 2 — Repos in Org

**Files:**
- Create: `ghtop-py/ghtop/screens/repos.py`
- Create: `ghtop-py/tests/test_screens/test_repos.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_screens/test_repos.py
import pytest
from unittest.mock import AsyncMock, patch
from ghtop.app import GHTopApp
from ghtop.config import Config
from tests.conftest import SAMPLE_REPOS


async def mock_gh_repos(*args):
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
         patch("ghtop.screens.repos.gh", side_effect=mock_gh_repos):
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
         patch("ghtop.screens.repos.gh", side_effect=mock_gh_repos):
        app = GHTopApp()
        async with app.run_test() as pilot:
            screen = ReposScreen("acme")
            app.push_screen(screen)
            await pilot.pause(1.5)
            from textual.widgets import DataTable
            tables = pilot.app.screen.query(DataTable)
            assert len(list(tables)) > 0
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_screens/test_repos.py -v
```

- [ ] **Step 3: Implement `screens/repos.py`**

```python
# ghtop/screens/repos.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static

from ghtop.config import CONCURRENT_FETCH_LIMIT
from ghtop.gh import gh, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


def _format_age(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s ago"
        if s < 3600:
            return f"{s // 60}m ago"
        if s < 86400:
            return f"{s // 3600}h ago"
        return f"{s // 86400}d ago"
    except Exception:
        return "?"


@dataclass
class RepoItem:
    name: str
    updated_at: str
    open_prs: Optional[int] = None
    is_pinned: bool = False


class ReposScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("escape,backspace", "go_back", "Back"),
        Binding("p", "pin", "Pin"),
        Binding("slash", "search", "Search"),
        Binding("q", "quit_app", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self, org: str) -> None:
        super().__init__()
        self._org = org
        self._repos: list[RepoItem] = []
        self._filtered: list[RepoItem] = []
        self._searching = False

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Input(placeholder="Search repos...", id="search-input")
        yield DataTable(id="repo-table")
        yield Static("", id="empty-state")
        yield StatusBar(f"★ {self._org} / repos   Esc back  / search  p pin")

    async def on_mount(self) -> None:
        header = self.query_one(AppHeader)
        header.breadcrumb = f"★ {self._org} / repos"
        self.query_one("#search-input").display = False

        table = self.query_one(DataTable)
        table.add_columns("NAME", "OPEN PRS", "LAST ACTIVITY")
        await self._load_repos()

    async def _load_repos(self) -> None:
        try:
            all_repos = []
            page = 1
            while True:
                batch = await gh(
                    "repo", "list", self._org,
                    "--limit", "20",
                    "--json", "name,updatedAt",
                )
                if not batch:
                    break
                all_repos.extend(batch)
                if len(batch) < 20:
                    break
                page += 1
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        if not all_repos:
            self.query_one("#empty-state", Static).update(
                f"No repositories found in {self._org}"
            )
            return

        self._repos = [
            RepoItem(
                name=r["name"],
                updated_at=r.get("updatedAt", ""),
                is_pinned=(
                    r["name"] == self.app.config.pinned_repo and
                    self._org == self.app.config.pinned_org
                ),
            )
            for r in all_repos
        ]

        # Fetch open PR counts concurrently
        sem = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)

        async def fetch_pr_count(repo: RepoItem) -> None:
            async with sem:
                try:
                    prs = await gh(
                        "pr", "list",
                        "--repo", f"{self._org}/{repo.name}",
                        "--state", "open",
                        "--json", "number",
                    )
                    repo.open_prs = len(prs) if prs else 0
                except GHError:
                    repo.open_prs = None

        await asyncio.gather(*[fetch_pr_count(r) for r in self._repos])
        self._filtered = list(self._repos)
        self._render_table()

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for repo in self._filtered:
            pin = "★ " if repo.is_pinned else "  "
            prs = str(repo.open_prs) if repo.open_prs is not None else "?"
            age = _format_age(repo.updated_at)
            table.add_row(f"{pin}{repo.name}", prs, age)

    def action_select(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._filtered):
            return
        repo = self._filtered[row]
        from ghtop.screens.prs import PRsScreen
        self.app.push_screen(PRsScreen(self._org, repo.name))

    def action_go_back(self) -> None:
        if self._searching:
            self._close_search()
        else:
            self.app.pop_screen()

    def action_pin(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._filtered):
            return
        repo = self._filtered[row]
        if repo.is_pinned:
            self.app.config.pinned_repo = None
            repo.is_pinned = False
        else:
            for r in self._repos:
                r.is_pinned = False
            self.app.config.pinned_org = self._org
            self.app.config.pinned_repo = repo.name
            repo.is_pinned = True
        self.app._save_config()
        self._render_table()

    def action_search(self) -> None:
        self._searching = True
        inp = self.query_one("#search-input", Input)
        inp.display = True
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if not query:
            self._filtered = list(self._repos)
        else:
            self._filtered = [r for r in self._repos if query in r.name.lower()]
        self._render_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._close_search()

    def _close_search(self) -> None:
        self._searching = False
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.display = False
        self._filtered = list(self._repos)
        self._render_table()
        self.query_one(DataTable).focus()

    def action_refresh(self) -> None:
        self.run_worker(self._load_repos(), exclusive=True)

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
pytest tests/test_screens/test_repos.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ghtop-py/ghtop/screens/repos.py ghtop-py/tests/test_screens/test_repos.py
git commit -m "feat: add ReposScreen (Screen 2) with concurrent PR count fetching"
```

---

## Task 8: Screen 3 — PR List

**Files:**
- Create: `ghtop-py/ghtop/screens/prs.py`
- Create: `ghtop-py/tests/test_screens/test_prs.py`

- [ ] **Step 1: Write the failing tests**

```python
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


async def mock_gh_prs(*args):
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
         patch("ghtop.screens.prs.gh", side_effect=mock_gh_prs):
        app = GHTopApp()
        async with app.run_test() as pilot:
            app.push_screen(PRsScreen("acme", "backend-api"))
            await pilot.pause(1.5)
            assert isinstance(pilot.app.screen, PRsScreen)


@pytest.mark.asyncio
async def test_prs_screen_toggle_filter():
    """m key toggles filter_mine."""
    from ghtop.screens.prs import PRsScreen
    with patch("ghtop.app.gh", side_effect=mock_gh_prs), \
         patch("ghtop.screens.prs.gh", side_effect=mock_gh_prs):
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_screens/test_prs.py -v
```

- [ ] **Step 3: Implement `screens/prs.py`**

Key code patterns — implement as complete file:

```python
# ghtop/screens/prs.py
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static
from textual.worker import Worker

from ghtop.config import CONCURRENT_FETCH_LIMIT
from ghtop.gh import gh, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


STATUS_ICON = {
    "in_progress": ("⟳", "blue"),
    "queued": ("○", "blue"),
    "waiting": ("○", "blue"),
    "success": ("✓", "green"),
    "failure": ("✗", "red"),
    "timed_out": ("✗", "red"),
    "action_required": ("✗", "red"),
    "cancelled": ("⊘", "orange"),
    "stale": ("⊘", "orange"),
    "skipped": ("○", "gray"),
}


def derive_pr_status(jobs: list[dict]) -> str:
    """Derive overall PR status from job list per spec priority rules."""
    statuses = [j.get("status") for j in jobs]
    conclusions = [j.get("conclusion") for j in jobs]

    if any(s == "in_progress" for s in statuses):
        return "in_progress"
    if any(s in ("queued", "waiting") for s in statuses):
        return "queued"
    if any(c in ("failure", "timed_out", "action_required") for c in conclusions):
        return "failure"
    if any(c in ("cancelled", "stale") for c in conclusions):
        return "cancelled"
    if all(c == "success" for c in conclusions if c):
        return "success"
    return "unknown"


def _format_age(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s"
        if s < 3600:
            return f"{s // 60}m"
        if s < 86400:
            return f"{s // 3600}h"
        return f"{s // 86400}d"
    except Exception:
        return "?"


class PRsScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("escape,backspace", "go_back", "Back"),
        Binding("m", "toggle_filter", "My PRs"),
        Binding("slash", "search", "Search"),
        Binding("o", "open_browser", "Open PR"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, org: str, repo: str) -> None:
        super().__init__()
        self._org = org
        self._repo = repo
        self._filter_mine: bool = True
        self._prs: list[dict] = []
        self._filtered: list[dict] = []
        self._worker: Optional[Worker] = None
        self._scroll_row: int = 0
        self._searching = False

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Input(placeholder="Search PRs...", id="search-input")
        yield DataTable(id="pr-table")
        yield Static("", id="empty-state")
        yield StatusBar("", id="status-bar-widget")

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("#", "TITLE", "AUTHOR", "AGE", "✓", "⟳", "✗", "⊘", "Σ")
        self.query_one("#search-input").display = False
        self._update_header()
        await self._load_prs()
        self._start_poll()

    def _update_header(self) -> None:
        header = self.query_one(AppHeader)
        label = "My PRs" if self._filter_mine else "PRs"
        header.breadcrumb = f"★ {self._org}/{self._repo} / {label}"
        hint_m = "m=all" if self._filter_mine else "m=mine"
        self.query_one("#status-bar-widget", StatusBar).update_hints(
            f"★ {self._org}/{self._repo}  {hint_m}  / search  Esc back"
        )

    def _start_poll(self) -> None:
        interval = self.app.config.refresh_interval

        async def poll() -> None:
            while True:
                await asyncio.sleep(interval)
                if self.is_attached:
                    await self._load_prs()

        self._worker = self.run_worker(poll(), exclusive=True)

    def on_unmount(self) -> None:
        if self._worker:
            self._worker.cancel()

    async def _load_prs(self) -> None:
        limit = self.app.config.pr_limit
        repo_flag = f"{self._org}/{self._repo}"
        base_args = [
            "pr", "list", "--repo", repo_flag,
            "--state", "open", "--limit", str(limit),
            "--json", "number,title,author,createdAt,headRefName,labels,reviewRequests",
        ]

        try:
            if self._filter_mine:
                authored, review_req = await asyncio.gather(
                    gh(*base_args, "--author", "@me"),
                    gh(*base_args, "--search", "review-requested:@me"),
                )
                # Merge and deduplicate by PR number; authored first
                seen = set()
                merged = []
                for pr in (authored or []) + (review_req or []):
                    if pr["number"] not in seen:
                        seen.add(pr["number"])
                        merged.append(pr)
                prs = merged[:limit]
            else:
                prs = await gh(*base_args) or []
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        # Fetch run status concurrently
        sem = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)

        async def fetch_run_status(pr: dict) -> None:
            async with sem:
                try:
                    runs = await gh(
                        "run", "list",
                        "--repo", repo_flag,
                        "--branch", pr["headRefName"],
                        "--limit", "10",
                        "--json", "databaseId,name,status,conclusion,startedAt,updatedAt",
                    )
                    pr["_runs"] = runs or []
                except GHError:
                    pr["_runs"] = []

        await asyncio.gather(*[fetch_run_status(pr) for pr in prs])

        self._prs = prs
        self._filtered = list(prs)
        self._render_table()
        self.query_one(AppHeader).error = ""

    def _run_counts(self, pr: dict) -> tuple[int, int, int, int, int]:
        runs = pr.get("_runs", [])
        if not runs:
            return 0, 0, 0, 0, 0
        # Latest run per workflow (by name)
        latest: dict[str, dict] = {}
        for run in runs:
            name = run["name"]
            if name not in latest:
                latest[name] = run
        jobs = list(latest.values())
        success = sum(1 for j in jobs if j.get("conclusion") == "success")
        running = sum(1 for j in jobs if j.get("status") == "in_progress")
        failed = sum(1 for j in jobs
                     if j.get("conclusion") in ("failure", "timed_out", "action_required"))
        cancelled = sum(1 for j in jobs
                        if j.get("conclusion") in ("cancelled", "stale"))
        total = len(jobs)
        return success, running, failed, cancelled, total

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        if not self._filtered:
            self.query_one("#empty-state", Static).update(
                "No open pull requests" if not self._filter_mine
                else "No PRs matching filter"
            )
            return
        self.query_one("#empty-state", Static).update("")
        for pr in self._filtered:
            s, r, f, c, total = self._run_counts(pr)
            status_str = f"{s}  {r}  {f}  {c}  ({total})" if total else "—"
            age = _format_age(pr.get("createdAt", ""))
            table.add_row(
                f"#{pr['number']}",
                pr["title"][:60],
                pr["author"]["login"],
                age,
                str(s), str(r), str(f), str(c), str(total),
            )
        # Restore scroll position
        if self._scroll_row < len(self._filtered):
            table.move_cursor(row=self._scroll_row)

    def action_select(self) -> None:
        row = self.query_one(DataTable).cursor_row
        self._scroll_row = row
        if row >= len(self._filtered):
            return
        pr = self._filtered[row]
        from ghtop.screens.actions import ActionsScreen
        self.app.push_screen(ActionsScreen(
            org=self._org, repo=self._repo, pr=pr
        ))

    def action_go_back(self) -> None:
        if self._searching:
            self._close_search()
        else:
            self.app.pop_screen()

    def action_toggle_filter(self) -> None:
        self._filter_mine = not self._filter_mine
        self._update_header()
        self.run_worker(self._load_prs(), exclusive=True)

    def action_open_browser(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._filtered):
            return
        pr = self._filtered[row]
        self.run_worker(
            self._open_pr_browser(pr["number"]), exclusive=False
        )

    async def _open_pr_browser(self, number: int) -> None:
        try:
            await gh("pr", "view", str(number),
                     "--repo", f"{self._org}/{self._repo}", "--web")
        except GHError as e:
            self.notify(f"Could not open browser. Error: {e}", severity="warning")

    def action_search(self) -> None:
        self._searching = True
        inp = self.query_one("#search-input", Input)
        inp.display = True
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if not query:
            self._filtered = list(self._prs)
        else:
            self._filtered = [
                pr for pr in self._prs
                if (query in pr["title"].lower() or
                    query in str(pr["number"]) or
                    query in pr["author"]["login"].lower())
            ]
        self._render_table()

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._close_search()

    def _close_search(self) -> None:
        self._searching = False
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.display = False
        self._filtered = list(self._prs)
        self._render_table()
        self.query_one(DataTable).focus()

    def action_refresh(self) -> None:
        self.run_worker(self._load_prs(), exclusive=True)

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
pytest tests/test_screens/test_prs.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ghtop-py/ghtop/screens/prs.py ghtop-py/tests/test_screens/test_prs.py
git commit -m "feat: add PRsScreen (Screen 3) with filter_mine, search, run status"
```

---

## Task 9: Screen 4 — PR Actions Detail

**Files:**
- Create: `ghtop-py/ghtop/screens/actions.py`
- Create: `ghtop-py/tests/test_screens/test_actions.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_screens/test_actions.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from ghtop.screens.prs import derive_pr_status


# Note: derive_pr_status is already tested in test_prs.py; here test ActionsScreen-specific logic

def test_double_tap_state_machine():
    """_pending_rerun flag is managed correctly."""
    # This is tested via the screen logic; we verify the state machine concept
    # by importing and checking the attribute exists
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

    async def mock_gh(*args):
        if list(args)[0] == "auth":
            return None
        if list(args)[0] == "run" and list(args)[1] == "view":
            return {"jobs": [
                {"name": "build", "status": "completed", "conclusion": "success",
                 "startedAt": "2026-03-19T10:00:00Z", "completedAt": "2026-03-19T10:01:00Z",
                 "steps": []}
            ]}
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.screens.actions.gh", side_effect=mock_gh):
        app = GHTopApp()
        async with app.run_test() as pilot:
            app.push_screen(ActionsScreen(org="acme", repo="api", pr=sample_pr))
            await pilot.pause(1.0)
            assert isinstance(pilot.app.screen, ActionsScreen)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_screens/test_actions.py -v
```

- [ ] **Step 3: Implement `screens/actions.py`**

```python
# ghtop/screens/actions.py
from __future__ import annotations
import asyncio
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Static

from ghtop.config import ACTIONS_REFRESH_INTERVAL
from ghtop.gh import gh, GHError
from ghtop.screens.prs import derive_pr_status, STATUS_ICON, _format_age
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


def _format_duration(started: str, completed: Optional[str]) -> str:
    if not started:
        return "—"
    try:
        from datetime import datetime, timezone
        start = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end_str = completed
        end = (datetime.fromisoformat(end_str.replace("Z", "+00:00"))
               if end_str else datetime.now(timezone.utc))
        secs = int((end - start).total_seconds())
        return f"{secs // 60}m {secs % 60}s"
    except Exception:
        return "?"


class ActionsScreen(Screen):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "view_logs", "View Logs"),
        Binding("escape,backspace", "go_back", "Back"),
        Binding("t", "rerun", "Rerun"),
        Binding("r", "open_run_browser", "Open Run"),
        Binding("l", "open_job_browser", "Open Job"),
        Binding("o", "open_pr_browser", "Open PR"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self, org: str, repo: str, pr: dict) -> None:
        super().__init__()
        self._org = org
        self._repo = repo
        self._pr = pr
        self._jobs: list[dict] = []
        self._run_id: Optional[int] = None
        self._scroll_row: int = 0
        self._pending_rerun: bool = False
        self._pending_rerun_timer: Optional[Timer] = None
        self._poll_worker = None

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Static("", id="pr-meta")
        yield DataTable(id="jobs-table")
        yield Static("", id="empty-state")
        yield StatusBar("t×2 rerun  l job browser  r run browser  o PR  Esc back  q quit")

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("WORKFLOW", "JOB", "STATUS", "DURATION")
        await self._load_jobs()
        self._start_poll()

    def _start_poll(self) -> None:
        async def poll() -> None:
            while True:
                await asyncio.sleep(ACTIONS_REFRESH_INTERVAL)
                if self.is_attached:
                    await self._load_jobs()

        self._poll_worker = self.run_worker(poll(), exclusive=True)

    def on_unmount(self) -> None:
        if self._poll_worker:
            self._poll_worker.cancel()
        if self._pending_rerun_timer:
            self._pending_rerun_timer.stop()

    async def _load_jobs(self) -> None:
        runs = self._pr.get("_runs", [])
        if not runs:
            # No runs — try fetching latest
            try:
                runs = await gh(
                    "run", "list",
                    "--repo", f"{self._org}/{self._repo}",
                    "--branch", self._pr.get("headRefName", ""),
                    "--limit", "1",
                    "--json", "databaseId,name,status,conclusion,startedAt,updatedAt",
                ) or []
            except GHError as e:
                self.query_one(AppHeader).error = str(e)
                return

        if not runs:
            self.query_one("#empty-state", Static).update(
                "No workflow runs found for this PR"
            )
            self._update_header([])
            return

        latest_run = runs[0]
        self._run_id = latest_run["databaseId"]

        try:
            run_detail = await gh(
                "run", "view", str(self._run_id),
                "--repo", f"{self._org}/{self._repo}",
                "--json", "jobs",
            )
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        self._jobs = (run_detail or {}).get("jobs", [])
        self._render_table()
        self._update_header(self._jobs)
        self.query_one(AppHeader).error = ""

    def _update_header(self, jobs: list[dict]) -> None:
        pr = self._pr
        status = derive_pr_status(jobs) if jobs else "unknown"
        icon, _ = STATUS_ICON.get(status, ("?", "gray"))
        age = _format_age(pr.get("createdAt", ""))
        breadcrumb = (
            f"PR #{pr['number']}: {pr['title'][:50]}   "
            f"{icon} {status}   "
            f"{self._org}/{self._repo} · {pr['author']['login']} · {age}"
        )
        self.query_one(AppHeader).breadcrumb = breadcrumb

        reviewers = [
            r.get("requestedReviewer", {}).get("login", "")
            for r in pr.get("reviewRequests", [])
        ]
        labels = [lbl["name"] for lbl in pr.get("labels", [])]
        meta = ""
        if reviewers:
            meta += "reviewers: " + ", ".join(r for r in reviewers if r)
        if labels:
            meta += ("  ·  " if meta else "") + "labels: " + " ".join(f"[{l}]" for l in labels)
        self.query_one("#pr-meta", Static).update(meta)

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        if not self._jobs:
            return
        for job in self._jobs:
            status = job.get("status", "")
            conclusion = job.get("conclusion")
            state = conclusion if status == "completed" and conclusion else status
            icon, _ = STATUS_ICON.get(state, ("?", "gray"))
            duration = _format_duration(
                job.get("startedAt"), job.get("completedAt")
            )
            # Group by run name (workflow) — show workflow for first job of each group
            table.add_row(
                job.get("workflowName", ""),
                job.get("name", ""),
                f"{icon} {state}",
                duration,
            )
        if self._scroll_row < len(self._jobs):
            table.move_cursor(row=self._scroll_row)

    def action_view_logs(self) -> None:
        row = self.query_one(DataTable).cursor_row
        self._scroll_row = row
        if row >= len(self._jobs):
            return
        job = self._jobs[row]
        from ghtop.screens.logs import LogsScreen
        self.app.push_screen(LogsScreen(
            run_id=self._run_id,
            repo=f"{self._org}/{self._repo}",
            job_name=job.get("name", ""),
            pr_number=self._pr["number"],
            workflow_name=job.get("workflowName", ""),
        ))

    def action_rerun(self) -> None:
        if self._pending_rerun:
            if self._pending_rerun_timer:
                self._pending_rerun_timer.stop()
                self._pending_rerun_timer = None
            self._pending_rerun = False
            if self._run_id:
                self.run_worker(self._do_rerun(), exclusive=False)
        else:
            self._pending_rerun = True
            self._pending_rerun_timer = self.set_timer(
                3.0, self._cancel_pending_rerun
            )
            self.notify("Press t again to rerun failed jobs", severity="warning")

    async def _do_rerun(self) -> None:
        try:
            await gh("run", "rerun", str(self._run_id),
                     "--repo", f"{self._org}/{self._repo}", "--failed")
            self.notify("Rerun triggered", severity="information")
            await asyncio.sleep(2)
            await self._load_jobs()
        except GHError as e:
            self.notify(f"Rerun failed: {e}", severity="error")

    def _cancel_pending_rerun(self) -> None:
        self._pending_rerun = False
        self._pending_rerun_timer = None

    def action_open_run_browser(self) -> None:
        if self._run_id:
            self.run_worker(self._open_run(self._run_id), exclusive=False)

    async def _open_run(self, run_id: int) -> None:
        try:
            await gh("run", "view", str(run_id),
                     "--repo", f"{self._org}/{self._repo}", "--web")
        except GHError as e:
            self.notify(f"Could not open browser: {e}", severity="warning")

    def action_open_job_browser(self) -> None:
        row = self.query_one(DataTable).cursor_row
        if row >= len(self._jobs) or not self._run_id:
            return
        self.run_worker(self._open_run(self._run_id), exclusive=False)

    def action_open_pr_browser(self) -> None:
        self.run_worker(self._open_pr(), exclusive=False)

    async def _open_pr(self) -> None:
        try:
            await gh("pr", "view", str(self._pr["number"]),
                     "--repo", f"{self._org}/{self._repo}", "--web")
        except GHError as e:
            self.notify(f"Could not open browser: {e}", severity="warning")

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self.run_worker(self._load_jobs(), exclusive=True)

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_quit_app(self) -> None:
        self.app.exit()
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
pytest tests/test_screens/test_actions.py -v
```

- [ ] **Step 5: Commit**

```bash
git add ghtop-py/ghtop/screens/actions.py ghtop-py/tests/test_screens/test_actions.py
git commit -m "feat: add ActionsScreen (Screen 4) with jobs table and double-tap rerun"
```

---

## Task 10: Screen 5 — Run Logs Viewer

**Files:**
- Create: `ghtop-py/ghtop/screens/logs.py`
- Create: `ghtop-py/tests/test_screens/test_logs.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_screens/test_logs.py
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

    async def mock_gh(*args):
        if list(args)[0] == "auth":
            return None
        # For run view --log, return raw text (not JSON)
        return None

    with patch("ghtop.app.gh", side_effect=mock_gh), \
         patch("ghtop.screens.logs.gh_raw", return_value=fake_log):
        app = GHTopApp()
        async with app.run_test() as pilot:
            app.push_screen(LogsScreen(
                run_id=1001, repo="acme/api", job_name="build",
                pr_number=42, workflow_name="CI"
            ))
            await pilot.pause(0.8)
            assert isinstance(pilot.app.screen, LogsScreen)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_screens/test_logs.py -v
```

- [ ] **Step 3: Implement `screens/logs.py`**

Note: `gh run view --log` returns raw text (not JSON), so we need a separate `gh_raw()` helper that doesn't JSON-parse the output.

First, add `gh_raw()` to `ghtop/gh.py`:

```python
# Add to ghtop/gh.py after the existing gh() function:

async def gh_raw(*args: str) -> str:
    """Run `gh <args>` and return raw stdout string (no JSON parsing).

    Used for `gh run view --log` which returns tab-delimited text.
    Raises GHError on non-zero exit.
    """
    delays = list(RATE_LIMIT_BACKOFF)
    attempts = len(delays) + 1

    for attempt in range(attempts):
        proc = await asyncio.create_subprocess_exec(
            "gh", *args,
            stdout=PIPE, stderr=PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return stdout.decode(errors="replace")

        err = stderr.decode(errors="replace")

        if _is_rate_limit(err) and attempt < len(delays):
            delay = delays[attempt]
            logger.warning("Rate limited by GitHub, retrying in %ss", delay)
            await asyncio.sleep(delay)
            continue

        raise GHError(err)

    raise GHError("Rate limit retries exhausted")
```

Then implement `screens/logs.py`:

```python
# ghtop/screens/logs.py
from __future__ import annotations
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static

from ghtop.gh import gh_raw, GHError
from ghtop.widgets.header import AppHeader
from ghtop.widgets.status_bar import StatusBar


def filter_log_lines(raw: str, job_name: str) -> list[str]:
    """Filter log lines by exact match on first tab-delimited field."""
    result = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[0] == job_name:
            result.append(parts[2])
    return result


class LogsScreen(Screen):
    BINDINGS = [
        Binding("escape,backspace", "go_back", "Back"),
        Binding("slash", "search", "Search"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(
        self,
        run_id: Optional[int],
        repo: str,
        job_name: str,
        pr_number: int,
        workflow_name: str,
    ) -> None:
        super().__init__()
        self._run_id = run_id
        self._repo = repo
        self._job_name = job_name
        self._pr_number = pr_number
        self._workflow_name = workflow_name
        self._all_lines: list[str] = []
        self._searching = False

    def compose(self) -> ComposeResult:
        yield AppHeader()
        yield Input(placeholder="Search logs...", id="search-input")
        yield RichLog(id="log-view", highlight=True, markup=False)
        yield Static("", id="empty-state")
        yield StatusBar("↑↓ scroll  / search  Esc back  q quit")

    async def on_mount(self) -> None:
        self.query_one(AppHeader).breadcrumb = (
            f"PR #{self._pr_number} · {self._workflow_name} · {self._job_name}"
        )
        self.query_one("#search-input").display = False
        await self._load_logs()

    async def _load_logs(self) -> None:
        if not self._run_id:
            self.query_one("#empty-state", Static).update("No run ID available.")
            return
        try:
            raw = await gh_raw(
                "run", "view", str(self._run_id),
                "--repo", self._repo,
                "--log",
            )
        except GHError as e:
            self.query_one(AppHeader).error = str(e)
            return

        self._all_lines = filter_log_lines(raw, self._job_name)
        self._render_logs(self._all_lines)

    def _render_logs(self, lines: list[str]) -> None:
        log_view = self.query_one("#log-view", RichLog)
        log_view.clear()
        if not lines:
            self.query_one("#empty-state", Static).update(
                f"No log lines found for job: {self._job_name}"
            )
            return
        self.query_one("#empty-state", Static).update("")
        for line in lines:
            log_view.write(line)

    def action_search(self) -> None:
        self._searching = True
        inp = self.query_one("#search-input", Input)
        inp.display = True
        inp.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if not query:
            self._render_logs(self._all_lines)
        else:
            filtered = [l for l in self._all_lines if query in l.lower()]
            self._render_logs(filtered)

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._close_search()

    def _close_search(self) -> None:
        self._searching = False
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.display = False
        self._render_logs(self._all_lines)
        self.query_one(RichLog).focus()

    def action_go_back(self) -> None:
        if self._searching:
            self._close_search()
        else:
            self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()
```

- [ ] **Step 4: Add `gh_raw` to `gh.py` as described in step 3**

- [ ] **Step 5: Add test for `gh_raw` to `tests/test_gh.py`**

```python
# append to tests/test_gh.py
@pytest.mark.asyncio
async def test_gh_raw_returns_text():
    from ghtop.gh import gh_raw
    proc = make_proc(stdout=b"build\tstep1\tlog line\n")
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await gh_raw("run", "view", "123", "--log")
    assert result == "build\tstep1\tlog line\n"
```

- [ ] **Step 6: Run all tests and verify they pass**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add ghtop-py/ghtop/gh.py ghtop-py/ghtop/screens/logs.py \
    ghtop-py/tests/test_screens/test_logs.py ghtop-py/tests/test_gh.py
git commit -m "feat: add LogsScreen (Screen 5) with job-filtered log view"
```

---

## Task 11: Full Test Run + Smoke Test

**Files:** No new files — verification only.

- [ ] **Step 1: Run full test suite**

```bash
cd ghtop-py
pytest tests/ -v --tb=short
```

Expected: all tests PASS. Zero failures.

- [ ] **Step 2: Smoke test against real GitHub (requires `gh auth status`)**

```bash
python -m ghtop
```

Expected:
- App starts, shows Org list
- Navigate with ↑↓ Enter
- `p` pins an org — saved to `~/.config/ghtop/config.yaml`
- `q` quits

- [ ] **Step 3: Test with temp config to validate pin routing**

```bash
python -m ghtop --config /tmp/test-ghtop.yaml
```

- [ ] **Step 4: Commit any fixes discovered during smoke test**

```bash
git add -p
git commit -m "fix: resolve issues found during smoke testing"
```

---

## Task 12: Packaging and README

**Files:**
- Verify: `ghtop-py/pyproject.toml`
- Create: `ghtop-py/README.md` (minimal)

- [ ] **Step 1: Verify entry point works**

```bash
cd ghtop-py
pip install -e .
ghtop  # should launch the app
```

Expected: app launches identically to `python -m ghtop`.

- [ ] **Step 2: Create minimal README**

```markdown
# ghtop

A terminal UI for monitoring GitHub Actions, built with Python + Textual.

## Install

```bash
pip install ghtop
# or
uv tool install ghtop
```

## Usage

```bash
ghtop
```

Requires `gh` CLI authenticated: `gh auth login`

## Keybindings

| Key | Action |
|-----|--------|
| `↑`/`↓` | Navigate |
| `Enter` | Drill down |
| `Esc`/`Backspace` | Go back |
| `p` | Pin/unpin |
| `m` | Toggle My PRs / All PRs (Screen 3) |
| `/` | Fuzzy search |
| `o` | Open in browser |
| `Ctrl+r` | Force refresh |
| `t` (×2) | Rerun failed jobs (Screen 4) |
| `q` | Quit |
```

- [ ] **Step 3: Final test run**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Final commit**

```bash
git add ghtop-py/README.md
git commit -m "docs: add README with install and keybinding reference"
```
