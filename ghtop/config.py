from __future__ import annotations
import logging
from dataclasses import dataclass
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
    pinned_owner: Optional[str] = None   # GitHub org or personal account login
    pinned_repo: Optional[str] = None
    refresh_interval: int = 30   # Screen 3 poll interval (seconds)
    pr_limit: int = 50           # max PRs after merge+dedup


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        return Config()
    try:
        raw = yaml.safe_load(path.read_text()) or {}
        pinned = raw.get("pinned") or {}
        # Accept both "owner" (new) and "org" (legacy) keys
        owner = pinned.get("owner") or pinned.get("org")
        return Config(
            pinned_owner=owner,
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
    if cfg.pinned_owner or cfg.pinned_repo:
        data["pinned"] = {}
        if cfg.pinned_owner:
            data["pinned"]["owner"] = cfg.pinned_owner
        if cfg.pinned_repo:
            data["pinned"]["repo"] = cfg.pinned_repo
    if cfg.refresh_interval != 30:
        data["refresh_interval"] = cfg.refresh_interval
    if cfg.pr_limit != 50:
        data["pr_limit"] = cfg.pr_limit
    path.write_text(yaml.safe_dump(data, default_flow_style=False))
