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
