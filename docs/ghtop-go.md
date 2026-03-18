# ghtop — Go Implementation Plan

## Goal
Production-grade, single-binary tool. Full feature parity with the Python MVP plus better performance and clean distribution. Built after Python MVP validates UX.

## Tech Stack
- **Go 1.22+**
- **Bubble Tea** — Elm MVU TUI framework (charmbracelet)
- **Lipgloss** — terminal styling and layout
- **Bubbles** — reusable components (table, spinner, textinput)
- **`github.com/cli/go-gh/v2`** — official gh Go library

## Project Structure
```
ghtop-go/
├── cmd/
│   └── ghtop/
│       └── main.go          # entry: startup check, init config, run TUI
├── internal/
│   ├── config/
│   │   └── config.go        # load/save ~/.config/ghtop/config.yaml + internal constants
│   ├── gh/
│   │   ├── client.go        # gh CLI subprocess wrapper, typed errors, backoff
│   │   ├── orgs.go          # ListOrgs() — includes personal account (deduplicated)
│   │   ├── repos.go         # ListRepos(org) — paginated 20/page, open PR count concurrent
│   │   ├── prs.go           # ListPRs(org, repo, filter) — includes headRefName
│   │   └── runs.go          # ListRuns, GetJobs, GetLogs, Rerun, OpenWeb
│   ├── model/
│   │   ├── types.go         # Org, Repo, PR, Run, Job structs
│   │   └── state.go         # AppState, NavStack, PinState, ErrorState
│   └── ui/
│       ├── app.go           # root Bubble Tea model, Init/Update/View, nav stack
│       ├── screens/
│       │   ├── orgs.go      # Screen 1
│       │   ├── repos.go     # Screen 2
│       │   ├── prs.go       # Screen 3 — My PRs default, concurrent run fetching (semaphore 10)
│       │   ├── actions.go   # Screen 4 — 10s poll
│       │   └── logs.go      # Screen 5 — Run Logs Viewer
│       ├── components/
│       │   ├── header.go    # breadcrumb + refresh status + error banner
│       │   ├── table.go     # styled wrapper around bubbles/table
│       │   ├── search.go    # fuzzy search overlay (bubbles/textinput) — case-insensitive, quality-ranked
│       │   └── statusbar.go # keybinding hints
│       └── styles/
│           └── styles.go    # all Lipgloss styles — single source of truth for colors/icons
├── go.mod
├── go.sum
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
- `OPEN PRS` from dedicated `gh pr list --state open --json number` call
- Open PR count fetched concurrently for all repos (goroutines, semaphore 10)
- Repos paginated 20 per page, all pages fetched
- Empty state: "No repositories found in <org>"

### Screen 3 — PR List
```
★ my-org/backend-api / My PRs   m=all   / search  Esc back   (filter_mine=ON)
★ my-org/backend-api / PRs      m=mine  / search  Esc back   (filter_mine=OFF)

#     TITLE                    AUTHOR   AGE    ✓  ⟳  ✗  ⊘  /Σ
▶ #42 fix: auth token expiry   you      2m     2  1  0  1  /4
  #41 feat: add rate limiting   alice    1h     1  0  2  0  /3
  #39 chore: update deps        bob      2d     5  0  0  0  /5
```
- **"My PRs" filter is ON by default** when entering Screen 3
- `m` toggles between "My PRs" (authored + review-requested) and all repo PRs
- Header label and hint update to reflect current state
- `✓` green / `⟳` blue / `✗` red / `⊘` orange / `○` blue (queued) / `○` gray (skipped) — defined in `styles.go`
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
- Status icon colors same as Screen 3 (from `styles.go`)
- Labels rendered as Lipgloss inline color blocks
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
- `/` opens live search overlay; case-insensitive, highlights matching lines ranked by match quality
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

All defined as constants in `internal/ui/styles/styles.go`.

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

**N+1 note:** Run status for Screen 3 requires 1 `gh run list` call per PR. Fetches run concurrently (goroutines, semaphore 10). Visible rows fetch first; off-screen rows in background. 30s TTL cache per branch.

**Known limitation:** `gh run list --branch <headRefName>` may return runs from other PRs sharing the same branch (e.g., stacked PRs). Accepted limitation — not filtered.

## Architecture: Elm MVU

Root `App` holds a nav stack. Only the top screen receives `Update` calls and is rendered. Navigation uses custom `tea.Msg` types. Each screen stores its own scroll position and filter state, restored when popped back onto the stack.

```go
type NavigateTo struct{ Screen Screen }
type NavigateBack struct{}

type App struct {
    stack  []Screen
    config config.Config
}

type Screen interface {
    Init() tea.Cmd
    Update(tea.Msg) (Screen, tea.Cmd)
    View() string
}
```

**Polling:** Screen 3 ticks every 30s; Screen 4 ticks every 10s. Ticking starts in `Init()` and stops naturally when the screen is popped (no more `Update` calls routed to it).

**Concurrent run fetching:**
```go
// internal/gh/runs.go
func FetchRunsForPRs(prs []PR, repo string) <-chan RunResult {
    sem := make(chan struct{}, 10)
    results := make(chan RunResult, len(prs))
    for _, pr := range prs {
        go func(pr PR) {
            sem <- struct{}{}
            defer func() { <-sem }()
            runs, err := ListRuns(repo, pr.HeadRefName)
            results <- RunResult{PR: pr, Runs: runs, Err: err}
        }(pr)
    }
    return results
}
```
Result delivered as `RunsLoadedMsg` back to the Bubble Tea program via `tea.Cmd`.

### `internal/config/config.go`
```go
// User-facing config (~/.config/ghtop/config.yaml)
type Config struct {
    Pinned          PinConfig `yaml:"pinned"`
    RefreshInterval int       `yaml:"refresh_interval"` // Screen 3 (default: 30s)
    PRLimit         int       `yaml:"pr_limit"`          // max PRs after merge+dedup (default: 50)
}

// Internal constants — not exposed in config file
const (
    ActionsRefreshInterval = 10 * time.Second // Screen 4 poll interval
    ConcurrentFetchLimit   = 10               // goroutine semaphore size
)

var RateLimitBackoff = []time.Duration{2 * time.Second, 4 * time.Second, 8 * time.Second}
```

### `internal/gh/client.go`
```go
func Run(args ...string) ([]byte, error) {
    var lastErr error
    for attempt := 0; attempt <= len(RateLimitBackoff); attempt++ {
        cmd := exec.Command("gh", args...)
        out, err := cmd.Output()
        if err == nil {
            return out, nil
        }
        var exitErr *exec.ExitError
        if errors.As(err, &exitErr) {
            ghErr := parseGHError(exitErr.Stderr)
            if isRateLimit(ghErr) && attempt < len(RateLimitBackoff) {
                time.Sleep(RateLimitBackoff[attempt])
                lastErr = ghErr
                continue
            }
            return nil, ghErr
        }
        return nil, &ErrNetwork{Cause: err}
    }
    return nil, lastErr
}
```
Typed errors: `ErrNotFound`, `ErrNotAuthenticated`, `ErrRateLimit`, `ErrNetwork`. Screens pattern-match to show appropriate inline banner or full-screen error.

### `internal/gh/orgs.go`
```go
func ListOrgs() ([]Org, error) {
    // 1. fetch orgs via /user/orgs
    // 2. fetch personal account via /user
    // 3. deduplicate: if personal login already in orgs list, skip duplicate
    // 4. append personal as Org{Login: user.Login, IsPersonal: true} at bottom
}
```

### `internal/gh/repos.go`
Paginates 20 repos per page; open PR counts fetched concurrently:
```go
func ListRepos(org string) ([]Repo, error) {
    var all []Repo
    page := 1
    for {
        batch, err := fetchReposPage(org, page, 20)
        if err != nil { return nil, err }
        all = append(all, batch...)
        if len(batch) < 20 { break }
        page++
    }
    return fetchOpenPRCounts(all) // concurrent, semaphore 10
}
```

### `internal/gh/prs.go` — My PRs merge
```go
func ListMyPRs(repo string, limit int) ([]PR, error) {
    authored, _ := listPRs(repo, "--author", "@me", limit)
    requested, _ := listPRs(repo, "--search", "review-requested:@me", limit)
    // merge: authored first, append requested, deduplicate by number, cap at limit
    return mergeAndDedup(authored, requested, limit), nil
}
```

### `internal/ui/screens/actions.go` — double-tap rerun
```go
type ActionsScreen struct {
    pendingRerun bool
    rerunTimer   tea.Cmd
}

func (s *ActionsScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        if msg.String() == "t" {
            if s.pendingRerun {
                s.pendingRerun = false
                return s, s.doRerun() // gh run rerun <selected_run_id> --failed
            }
            s.pendingRerun = true
            return s, tea.Batch(
                s.showHint("Press t again to rerun"),
                tea.Tick(3*time.Second, func(time.Time) tea.Msg {
                    return rerunTimeoutMsg{}
                }),
            )
        }
    case rerunTimeoutMsg:
        s.pendingRerun = false
    }
    // ...
}
```

### `internal/ui/screens/logs.go`
- Receives `run_id`, `repo`, `job_name` from Screen 4
- Calls `gh run view <run-id> --repo <repo> --log`
- Filters lines by exact match on first `\t`-delimited field (job name)
- No user-facing job filter — job is fixed from Screen 4 selection

### `internal/ui/components/search.go`
Live filter — fires on every `tea.KeyMsg` while overlay is visible. Case-insensitive, results ranked by match quality. `Esc` closes and clears filter value.

### `internal/ui/styles/styles.go`
Single source of truth for all colors, status icons, and column truncation helpers.

```go
func StatusIcon(status, conclusion string) (icon string, style lipgloss.Style) {
    if status == "in_progress" {
        return "⟳", BlueStyle
    }
    if status == "queued" || status == "waiting" {
        return "○", BlueStyle
    }
    switch conclusion {
    case "success":
        return "✓", GreenStyle
    case "failure", "timed_out", "action_required":
        return "✗", RedStyle
    case "cancelled", "stale":
        return "⊘", OrangeStyle
    case "skipped":
        return "○", GrayStyle
    }
    return "○", GrayStyle
}

func OverallPRStatus(jobs []Job) (icon string, style lipgloss.Style) {
    // Priority: in_progress > queued/waiting > failure > cancelled > success > gray
}
```

Truncation: all string columns clipped with `…` to fit available terminal width — no minimum width enforced.

### Browser open fallback
If `gh pr view --web` or `gh run view --web` returns non-zero (e.g., no browser in SSH), show the URL in a Bubble Tea notification so the user can copy it.

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

## Build & Distribution
```bash
go build -o ghtop ./cmd/ghtop

# Cross-compile
GOOS=darwin GOARCH=arm64 go build -o ghtop-darwin-arm64 ./cmd/ghtop
GOOS=linux  GOARCH=amd64 go build -o ghtop-linux-amd64  ./cmd/ghtop
```
Single static binary. No runtime dependencies beyond the `gh` CLI.

## Verification
```bash
./ghtop                                          # run against real GitHub account
go test ./...                                    # unit tests (mock exec.Command via interface)
go test ./internal/gh/... -tags=integration      # integration tests against real gh CLI
go build ./... && go vet ./...
```
