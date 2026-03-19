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
