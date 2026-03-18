# ghtop — Python MVP Plan

## Goal
Working, shippable TUI in ~1–2 weeks. Validates UX and all `gh` CLI interactions before Go investment.

## Tech Stack
- **Python 3.10+**
- **Textual** `>=0.80,<1.0` — async TUI framework (same as cctop reference)
- No other runtime deps — `gh` CLI is external
- `uv` or pip for packaging

## Project Structure
```
ghtop-py/
├── ghtop/
│   ├── __main__.py          # entry point: python -m ghtop
│   ├── app.py               # Textual App class, startup check, screen routing
│   ├── config.py            # load/save ~/.config/ghtop/config.yaml + internal constants
│   ├── gh.py                # all gh CLI subprocess calls (async), error handling
│   ├── screens/
│   │   ├── orgs.py          # Screen 1 — Org Selector
│   │   ├── repos.py         # Screen 2 — Repos in Org
│   │   ├── prs.py           # Screen 3 — PR List (default: My PRs)
│   │   ├── actions.py       # Screen 4 — PR Actions Detail
│   │   └── logs.py          # Screen 5 — Run Logs Viewer
│   └── widgets/
│       ├── header.py        # breadcrumb + refresh status + error banner
│       └── status_bar.py    # keybinding hints at bottom
├── pyproject.toml
└── README.md
```

## Screens

### Screen 1 — Org Selector
```
ghtop   ↑↓ navigate  Enter select  p pin  q quit

Organizations (3)
▶ ★ my-org
    acme-corp
    personal
    [you] dima
```
- `★` marks the pinned org
- Personal account appended at bottom with `[you]` marker, fetched via `gh api /user`
- If personal account login appears in `/user/orgs` response, deduplicate — show once with `[you]` marker
- Empty state: "No organizations found. Make sure you are authenticated: gh auth status"

### Screen 2 — Repos in Org
```
★ my-org / repos (5)   Esc back  / search  p pin

NAME            OPEN PRS   LAST ACTIVITY
▶ ★ backend-api   3          2m ago
    frontend       1          1h ago
    infra          0          3d ago
```
- `OPEN PRS` from dedicated `gh pr list --state open --json number` call (not `openIssuesCount`)
- Open PR count fetched concurrently for all repos with `asyncio.Semaphore(10)`
- Repos paginated 20 per page, all pages fetched
- Empty state: "No repositories found in <org>"

### Screen 3 — PR List
```
★ my-org/backend-api / My PRs   m=all   / search  Esc back   (filter_mine=ON)
★ my-org/backend-api / PRs      m=mine  / search  Esc back   (filter_mine=OFF)

#     TITLE                    AUTHOR   AGE    ✓  ⟳  ✗  ⊘  (Σ)
▶ #42 fix: auth token expiry   you      2m     2  1  0  1  (4)
  #41 feat: add rate limiting   alice    1h     1  0  2  0  (3)
  #39 chore: update deps        bob      2d     5  0  0  0  /5)
```
- **"My PRs" filter is ON by default** when entering Screen 3
- `m` toggles between "My PRs" (authored + review-requested) and all repo PRs
- Header label and hint update to reflect current state
- `✓` green / `⟳` blue / `✗` red / `⊘` orange / `○` blue (queued) / `○` gray (skipped)
- `Σ` = total number of distinct workflows (latest run per workflow counted once)
- Counts reflect latest run per workflow; PRs with no runs show `—`
- Empty state: "No open pull requests" / "No PRs matching filter"
- Filter state and scroll position **restored** when navigating back from Screen 4

### Screen 4 — PR Actions Detail
```
PR #42: fix: auth token expiry   ⟳ running   my-org/backend-api · you · 2m ago
reviewers: alice, bob  ·  labels: [bug] [backend] [priority:high]

WORKFLOW        JOB       STATUS       DURATION
▶ CI Pipeline   build     ⟳ running    1m 23s
  CI Pipeline   lint      ✓ passed     0m 42s
  CI Pipeline   test      ○ queued     —
  Deploy        preview   ○ skipped    —
```
- Status icon colors same as Screen 3
- **Overall PR status** in header derived from jobs using this priority:
  1. Any `in_progress` → `⟳` blue
  2. Any `queued`/`waiting` → `○` blue
  3. Any `failure`/`timed_out`/`action_required` → `✗` red
  4. Any `cancelled`/`stale` → `⊘` orange
  5. All `success` → `✓` green
  6. Otherwise → `○` gray
- `[t]` double-tap reruns **selected run** with `--failed` (only failed jobs within that run)
- `[l]` opens selected job's run page in browser
- `[r]` opens current run in browser
- `Enter` on a job row drills into Screen 5 (Run Logs for that specific job)
- Auto-refreshes every **10s**
- Empty state: "No workflow runs found for this PR"
- Scroll position **restored** when navigating back from Screen 5

### Screen 5 — Run Logs Viewer
```
PR #42 · CI Pipeline · build   ⟳ running   Esc back  / search  q quit

[2m 01s] Setting up Node.js 20
[2m 03s] Cache not found for input keys: node-modules-...
[2m 05s] ▶ Run npm ci
[2m 12s] added 1234 packages in 7s
[2m 13s] ✓ npm ci completed
```
- Shows logs for the **specific job selected in Screen 4** only
- `gh run view --log` output format is `<job_name>\t<step_name>\t<log_line>`; filter by exact job name match on first field
- `↑`/`↓` scroll through log lines
- `/` opens live search overlay within logs; case-insensitive, results ranked by match quality
- `Esc` / `Backspace` returns to Screen 4
- `q` quits app

## Status Icon Reference

| State | Icon | Color |
|-------|------|-------|
| `in_progress` | `⟳` | blue |
| `queued` / `waiting` | `○` | blue |
| `success` | `✓` | green |
| `failure` / `timed_out` / `action_required` | `✗` | red |
| `cancelled` / `stale` | `⊘` | orange |
| `skipped` | `○` | gray |

## Keybindings

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate list |
| `Enter` | Drill down |
| `Esc` / `Backspace` | Go back one level (restores scroll + filter state) |
| `p` | Pin/unpin (toggle; replaces existing pin) |
| `m` | Toggle "my PRs" / all PRs filter (Screen 3) |
| `/` | Fuzzy search overlay — case-insensitive, ranked by quality; Esc closes and clears filter |
| `o` | Open PR in browser (all screens) |
| `Ctrl+r` | Force refresh current screen (all screens) |
| `r` | Open current run in browser (Screen 4 only) |
| `t` | Double-tap: rerun selected run (failed jobs only) (Screen 4) |
| `l` | View selected job's run page in browser (Screen 4) |
| `q` | Quit app (any screen) |

## Fuzzy Search Scope

| Screen | Searched fields |
|--------|----------------|
| Screen 2 | repo name |
| Screen 3 | PR title, PR number, author login |
| Screen 4 | workflow name, job name |
| Screen 5 | log line content |

All search: case-insensitive, results ranked by match quality.

## "My PRs" Filter
- **ON by default** when entering Screen 3
- Two `gh pr list` calls merged, deduplicated by PR number, capped at `pr_limit`:
  1. `gh pr list --author @me` — authored PRs (shown first)
  2. `gh pr list --search "review-requested:@me"` — awaiting review (appended)
- Combined result deduplicated and capped at `pr_limit` total

## Pin Behavior
- `p` on unpinned item → pins it (replaces any existing pin at any level)
- `p` on pinned item → unpins it
- Pinning a repo clears any existing org-only pin; pinning an org clears any existing repo pin
- Pinned org → opens Screen 2 directly on launch
- Pinned repo → opens Screen 3 (My PRs) directly on launch
- If pinned org/repo no longer exists on launch → show warning, clear pin, navigate to Screen 1
- Config saved to `~/.config/ghtop/config.yaml`

## GitHub API Commands

| Data | Command |
|------|---------|
| List orgs | `gh api /user/orgs --paginate` |
| Personal account | `gh api /user` |
| List repos | `gh repo list <org> --limit 20 --json name,updatedAt` (paginate all pages) |
| Open PR count per repo | `gh pr list --repo <org/repo> --state open --json number` |
| List PRs | `gh pr list --repo <org/repo> --state open --limit <pr_limit> --json number,title,author,createdAt,headRefName,labels,reviewRequests` |
| My PRs (authored) | add `--author @me` |
| My PRs (review requested) | `--search "review-requested:@me"` |
| Latest runs per PR | `gh run list --repo <org/repo> --branch <headRefName> --limit 10 --json databaseId,name,status,conclusion,startedAt,updatedAt` |
| Run jobs | `gh run view <run-id> --repo <org/repo> --json jobs` |
| Run logs | `gh run view <run-id> --repo <org/repo> --log` (filter by exact job name on first `\t`-delimited field) |
| Open PR in browser | `gh pr view <number> --repo <org/repo> --web` |
| Trigger rerun (failed jobs) | `gh run rerun <run-id> --repo <org/repo> --failed` |
| View run in browser | `gh run view <run-id> --repo <org/repo> --web` |

**N+1 note:** Run status for Screen 3 requires 1 `gh run list` call per PR. Fetches are concurrent with a semaphore of 10. Visible rows fetch first; off-screen rows fetch in background. 30s TTL cache per branch.

**Known limitation:** `gh run list --branch <headRefName>` may return runs from other PRs sharing the same branch (e.g., stacked PRs). Accepted limitation — not filtered.

## Key Implementation Notes

### `config.py` — user config + internal constants
```python
# User-facing config (~/.config/ghtop/config.yaml)
@dataclass
class Config:
    pinned_org: str | None = None
    pinned_repo: str | None = None
    refresh_interval: int = 30   # Screen 3 poll interval (seconds)
    pr_limit: int = 50           # max PRs after merge+dedup

# Internal constants (not exposed in config file)
ACTIONS_REFRESH_INTERVAL = 10   # Screen 4 poll interval (seconds)
CONCURRENT_FETCH_LIMIT = 10     # asyncio.Semaphore size
RATE_LIMIT_BACKOFF = [2, 4, 8]  # retry delays in seconds
```

### `gh.py` — async subprocess wrapper
```python
async def gh(*args) -> dict | list | None:
    proc = await asyncio.create_subprocess_exec(
        "gh", *args,
        stdout=PIPE, stderr=PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise GHError(stderr.decode())
    return json.loads(stdout) if stdout.strip() else None
```
- `GHError` caught at screen level → inline error banner
- Concurrent run fetches use `asyncio.gather` with `asyncio.Semaphore(10)`
- **Rate limit backoff:** detect "rate limit" in stderr or HTTP 429 → retry after 2s, 4s, 8s (max 3 retries)

### `app.py` — startup + routing
```python
async def on_mount(self):
    try:
        await gh("auth", "status")
    except GHError:
        self.push_screen(ErrorScreen("Not authenticated. Run: gh auth login"))
        return
    # check config for pinned repo/org → push appropriate screen
```
- `push_screen()` / `pop_screen()` for navigation
- Each screen is a Textual `Screen` subclass
- Each screen stores scroll position and filter state; restored on pop

### `screens/prs.py`
- Textual `DataTable` for PR list
- Background `Worker` polls every 30s; stopped on `on_unmount` (active screen only)
- **`filter_mine` starts as `True`** — first load fetches authored + review-requested
- `m` key toggles `filter_mine`, re-fetches accordingly
- Combined "My PRs" results deduplicated by PR number and capped at `pr_limit`
- `/` key shows Textual `Input` overlay; **live filters rows in memory as you type** (case-insensitive, quality-ranked); `Esc` closes and clears

### `screens/actions.py`
- Static header widget: PR title + overall status (derived per priority rules above) + path
- Metadata line 2: Rich markup for reviewers + label chips (colored)
- `DataTable` for jobs; polls every **10s**
- Double-tap `t` reruns **selected run** with `--failed`:
  ```python
  _pending_rerun: bool = False
  _pending_rerun_timer: Timer | None = None

  def on_key_t(self):
      if self._pending_rerun:
          self._cancel_pending_timer()
          asyncio.create_task(self._do_rerun())  # gh run rerun <selected_run_id> --failed
      else:
          self._pending_rerun = True
          self._pending_rerun_timer = self.set_timer(3, self._cancel_pending)
          self.notify("Press t again to rerun", severity="warning")
  ```

### `screens/logs.py`
- Receives `run_id`, `repo`, `job_name` from Screen 4
- Calls `gh run view <run-id> --repo <repo> --log`
- Filters lines by exact match on first `\t`-delimited field (job name)
- `ScrollableContainer` or `RichLog` widget for scrollable output
- `/` key shows inline search; case-insensitive, highlights matching lines ranked by quality

### Browser open fallback
- `gh pr view --web` / `gh run view --web` — if `gh` returns non-zero (e.g., no browser in SSH), show URL in a notification banner so user can copy it

### Column truncation
- All string columns truncated with `…` to fit available terminal width
- Textual handles layout; no minimum terminal width enforced

## Error Handling

| Condition | Behavior |
|-----------|----------|
| `gh` not found | Full-screen error: "gh CLI not found. Install from https://cli.github.com" |
| Not authenticated | Full-screen error: "Not authenticated. Run: gh auth login" |
| Non-zero `gh` exit | Inline error banner with stderr; stale data retained |
| Rate limit | Exponential backoff: retry after 2s, 4s, 8s; show "⚠ Rate limited" in header |
| Network error | "⚠ Offline — last updated Xs ago" in header; retry on next poll |
| Malformed config | Log warning, use defaults |
| Pinned item gone | Warning shown, pin cleared, navigate to Screen 1 |
| Browser open fails | Show URL in notification banner |

## Config File (`~/.config/ghtop/config.yaml`)
```yaml
pinned:
  org: my-org        # optional
  repo: backend-api  # optional; setting repo clears org-only pin
refresh_interval: 30 # seconds — Screen 3 poll interval
pr_limit: 50         # max PRs after merge+dedup of My PRs calls
```

## Installation
```bash
pip install ghtop
# or
uv tool install ghtop
```

## Verification
```bash
python -m ghtop                          # run against real GitHub account
pytest tests/ -v                         # unit tests (mock gh subprocess)
python -m ghtop --config /tmp/test.yaml  # test with temp config
```
