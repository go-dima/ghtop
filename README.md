# ghtop

A terminal UI for monitoring GitHub Actions — browse orgs, repos, and pull requests, watch CI status live, and trigger reruns without leaving the terminal.

Inspired by [k9s](https://github.com/derailed/k9s) and [htop](https://github.com/htop-dev/htop).

## Requirements

- Python 3.10+
- [`gh` CLI](https://cli.github.com) installed and authenticated (`gh auth login`)

## Install

**From PyPI (once published):**
```bash
pip install ghtop
# or
uv tool install ghtop
```

**From this repo:**
```bash
pip install /path/to/ghtop
# or
pip install git+https://github.com/<user>/ghtop
# or, for development
pip install -e /path/to/ghtop
```

## Usage

```bash
ghtop
```

Optional flag:
```bash
ghtop --config /path/to/config.yaml   # use a custom config file
```

## Navigation

ghtop is a 5-screen hierarchy you navigate with the keyboard:

```
Organizations  →  Repos in Org  →  PR List  →  PR Actions  →  Run Logs
```

## Keybindings

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate list |
| `Enter` | Drill down |
| `Esc` / `Backspace` | Go back |
| `p` | Pin / unpin current item |
| `m` | Toggle My PRs / All PRs (PR List screen) |
| `/` | Search / filter (case-insensitive) |
| `o` | Open PR in browser |
| `Ctrl+r` | Force refresh |
| `r` | Open current run in browser (Actions screen) |
| `l` | Open selected job in browser (Actions screen) |
| `t` `t` | Rerun failed jobs (double-tap, Actions screen) |
| `q` | Quit |

## Configuration

Config is stored at `~/.config/ghtop/config.yaml` (created automatically).

```yaml
pinned:
  org: my-org         # skip org selector on launch
  repo: backend-api   # skip to PR list on launch
refresh_interval: 30  # seconds between PR list polls
pr_limit: 50          # max PRs shown in My PRs view
```

Pin an org or repo by pressing `p` while it's selected. The next launch jumps straight there.

## Development

```bash
# Install with dev dependencies (requires uv)
uv sync --dev

# Run tests
uv run pytest

# Run the app
uv run ghtop
```
