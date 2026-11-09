# ghtop: detailed implementation plan

*   **Status:** Draft
*   **Design doc:** [ghtop.md](../designs/ghtop.md)
*   **Architecture:** [architecture.md](../architecture.md)

Every file the first version creates, changes, moves or deletes, with what it
holds and why. No code here; interfaces are named, not written. Detailed
behavior lives in the spec files listed in [CHECKLIST.md](./CHECKLIST.md); this
plan links to them instead of repeating them.

## Starting point

The repo `go-dima/ghtop` has only docs on `main`: `ghtop.md`, `docs/ghtop-go.md`,
`docs/ghtop-python-mvp.md`, plus the new planning files. The Python attempt
lives on the remote branch `feat/python-mvp` and is left untouched (not merged,
not deleted).

## Libraries

| Library | Use | Why this one |
|---|---|---|
| `github.com/charmbracelet/bubbletea` | update loop, messages, commands | decided stack; gh-dash reference |
| `github.com/charmbracelet/bubbles` | table, viewport, key bindings, help | same family; gh-dash uses it |
| `github.com/charmbracelet/lipgloss` | styles, layout, width math | same family |
| `github.com/BurntSushi/toml` | config | reports unknown keys (`MetaData.Undecoded`), so typos in config fail loudly |
| standard library only for everything else | `os/exec`, `net/http`, `regexp`, `log/slog`, `encoding/json` | fewer dependencies to update |

Go version: the current stable release at start of coding, recorded in `go.mod`
(Go is not installed on the author's machine yet). Minimum tool versions,
checked at start and by `ghtop doctor`: `gh` 2.103.3, `twg` 1.3.8.

## Milestones

Each milestone ends with a working binary and passing tests. Order matters:
read-only first, actions last.

| # | Milestone | Ends with |
|---|---|---|
| M0 | UI spike (throwaway) | one table from one `gh` search, arrows, `o`, `r`, resize; notes in `spike/README.md` |
| M1 | Skeleton + Open view, read-only | config load, `gh` runner, Open view search, table, header, status bar, help |
| M2 | All four views | Merged, Review-requested (+ background count), Involved; view switching with cached rows |
| M3 | Jira | key extraction, ticket status column, `t`, availability check |
| M4 | Jenkins state | URL trust, last-build state, `b` (open in browser), availability check, VPN detection |
| M5 | PR detail + Actions view | `Enter` detail, `a` Actions runs/jobs/failed steps |
| M6 | Actions | confirm dialog, re-run failed, update branch, Jenkins Build Now + presets + queue follow, Jira quick move |
| M7 | Operability | `ghtop doctor`, `--debug` log with redaction, error classes complete, leak guard |

## Target files

Paths are relative to the repo root.

### Repo root

#### 1. `go.mod`, `go.sum` (Create)

*   **Type / Scope**: Go module.
*   **Proposed Changes**: module `github.com/go-dima/ghtop`; the libraries
    above. Why: required for a Go build.

#### 2. `cmd/ghtop/main.go` (Create)

*   **Type / Scope**: entry point.
*   **Proposed Changes**: parses flags (`--config <path>`, `--debug`,
    `--version`) and the `doctor` subcommand; loads config; builds the
    providers (gh runner, Jira, Jenkins) and hands them to the UI; exits with a
    clear message and non-zero code on config errors. Why: one place that wires
    everything, so packages do not build their own dependencies.

#### 3. `config.example.toml` (Create)

*   **Type / Scope**: sample config, placeholders only.
*   **Proposed Changes**: the TOML example from [config.md](./config.md), every
    key commented. Why: first run with no config prints its path and points
    here.

#### 4. `README.md` (Create)

*   **Type / Scope**: user docs.
*   **Proposed Changes**: what ghtop is, prerequisites (`gh` logged in; `twg`
    and `JENKINS_TOKEN` optional), install (`go install`), config path, key
    list (generated from the keymap, see file 40), `ghtop doctor`, link to
    `docs/`. Why: the repo has no README.

#### 5. `ghtop.md` (Move -> `docs/archive/ghtop.md`)

*   **Proposed Changes**: moved unedited with a "superseded by
    docs/designs/ghtop.md" line on top. Why: keeps history, removes the
    old spec from the root.

#### 6. `.gitignore` (Create)

*   **Proposed Changes**: build output, `dist/`, local config copies
    (`*.local.toml`), debug logs. Why: keep binaries and private files out of
    git.

#### 7. `Makefile` (Create)

*   **Proposed Changes**: targets `build`, `test`, `lint`, `cover`, `smoke`
    (runs the manual `gh` command list, see file 22), `leakcheck` (see file
    9). Why: one set of commands for me and CI.

#### 8. `.golangci.yml` (Create)

*   **Proposed Changes**: enables `govet`, `staticcheck`, `errcheck`,
    `gosec` (flags `exec.Command` with non-constant names and weak TLS),
    `revive`. Why: catches the mistakes the design rules forbid (shell use,
    ignored errors).

#### 9. `scripts/leakcheck.sh` and `.githooks/pre-commit` (Create)

*   **Type / Scope**: leak guard.
*   **Proposed Changes**: `leakcheck.sh` greps staged files for each line of a
    private denylist at `~/.config/ghtop/leakguard.txt` (org name, Jira site,
    key prefix, Jenkins host, user name); fails the commit on a hit; does
    nothing if the denylist is missing. The hook calls it; `make hooks` sets
    `core.hooksPath`. Why: the repo is public and the private values cannot be
    listed in it.

#### 10. `.github/workflows/ci.yml` (Create)

*   **Proposed Changes**: on push and PR: `go build ./...`, `go vet ./...`,
    `golangci-lint`, `go test -race ./...`, coverage report. No secrets, no
    network tests. Why: every change is checked the same way.

#### 11. `.github/pull_request_template.md` (Create)

*   **Proposed Changes**: checklist with "docs/architecture.md updated if the
    structure changed" and "decision recorded in docs/decisions/ if one was
    made". Why: keeps diagrams and decisions in step with code (open task 3 in
    [TASKS.md](./TASKS.md); drop this file if the answer is no).

#### 12. `LICENSE` (Create)

*   **Proposed Changes**: MIT. Why: the repo is public and has no license;
    gh-dash and the other reference tools use MIT.

### Config

#### 13. `internal/config/config.go` (Create)

*   **Type / Scope**: config types and loading.
*   **Proposed Changes**: types for `[github]`, `[tracker]`, `[jenkins]`,
    `[ui]`; path resolution (`--config`, then `GHTOP_CONFIG`, then
    `$XDG_CONFIG_HOME/ghtop/config.toml`, then `~/.config/ghtop/config.toml`,
    never the macOS Application Support folder); `version` check (unknown or
    missing version -> error with the path); unknown keys -> error listing
    them; validation (org required, regexes compile, hosts have no scheme,
    durations parse, `${VAR}` expanded only where allowed); a found
    `config.yaml` from the old attempt -> error with a hint. Never writes the
    file. Why: one place that turns the file into checked values; no silent
    defaults that widen the search.

#### 14. `internal/config/config_test.go`, `internal/config/testdata/*.toml` (Create)

*   **Proposed Changes**: cases: valid full, minimal (GitHub only), missing
    org, bad regex, unknown key, wrong version, old YAML present, env
    expansion. Placeholders only.

### Model

#### 15. `internal/model/row.go` (Create)

*   **Type / Scope**: shared data types.
*   **Proposed Changes**: `PRID` (`owner/repo#N`), `Row`, `Check`, `Ticket`,
    `MergeState`, `CIState` with the worst-first order and `Worst()`, `Roles`;
    title kept as written, plus `DisplayTitle(stripLeadingKey bool)`. Details
    in `core/data-model.md`. Why: providers fill these, the UI reads them; no
    provider types leak into the UI.

#### 16. `internal/model/source.go` (Create)

*   **Proposed Changes**: `Source` (GitHub, Actions, Jira, Jenkins),
    `SourceState` (available, last ok, last error, stale), `ErrorClass` (tool
    missing, auth expired, network blocked, rate limited, upstream timeout,
    not found, truncated, config invalid, action rejected) with the fix-hint
    text per class. Why: one error vocabulary for header, status bar and logs.

#### 17. `internal/model/store.go` (Create)

*   **Proposed Changes**: row store keyed by `PRID` per view, merge functions
    per source (GitHub rows replace; Jira and Jenkins fill fields), sort
    (CI failed -> ready -> rest, then ticket status, then last commit), cursor
    anchoring by `PRID`. Pure functions, no I/O. Why: the logic most likely to
    break is testable without a terminal.

#### 18. `internal/model/*_test.go` (Create)

*   **Proposed Changes**: worst-state order, merge of partial results,
    cursor stays on the same PR after re-sort, title strip only at the start.

### Process runner

#### 19. `internal/proc/runner.go` (Create)

*   **Type / Scope**: the only code that starts processes.
*   **Proposed Changes**: `Runner` interface (`Run(ctx, name, args) -> stdout,
    stderr, exit code`); exec implementation with: argument list only (no
    shell), fixed env additions (`GH_PROMPT_DISABLED=1`, `GH_PAGER=`,
    `NO_COLOR=1`), timeout per call, cancel on context, cap on processes
    running at once, debug-log line per call (name, args without bodies,
    duration, exit code). Used by both the `gh` and `twg` providers. Why: one
    audited place for subprocess rules (decision 0009).

#### 20. `internal/proc/fake.go`, `internal/proc/runner_test.go` (Create)

*   **Proposed Changes**: a fake runner that returns recorded outputs by
    command; tests for timeout, cancel and the concurrency cap.

### GitHub

#### 21. `internal/github/provider.go` (Create)

*   **Proposed Changes**: `PRSource` interface: `Search(ctx, view)`,
    `ReviewRequestedCount(ctx)`, `BehindBy(ctx, rows)`, `UpdateBranch(ctx,
    pr)`; the `gh` implementation that calls `proc.Runner`. Why: domain-level
    interface so a `go-gh` version can replace it (decision 0009).

#### 22. `internal/github/commands.go` (Create)

*   **Proposed Changes**: the closed list of `gh` commands ghtop runs, one
    named entry each (for example "search open PRs": `gh api graphql -f
    query=@open.graphql -F q=...`). The same list feeds `make smoke`, which
    prints and runs each command with my config's values. Details in
    `services/github.md`. Why: no command is built anywhere else.

#### 23. `internal/github/queries/*.graphql` (Create)

*   **Proposed Changes**: `open.graphql` (full: reviews, threads, comments,
    checks, merge state), `closed.graphql` (light: reviews, rollup state),
    `count.graphql` (`issueCount` only), `behind.graphql` (one repository
    compare, with variables), `run_id.graphql` (check suite -> workflow run
    id). All take values as variables, all request `rateLimit`. Embedded in
    the binary. Why: queries reviewable as files; no values pasted into query
    text.

#### 24. `internal/github/parse.go` (Create)

*   **Proposed Changes**: JSON -> `model.Row`; check classification (Actions by
    app slug, Jenkins by `jenkins.Match`, other); cap warnings; rate-limit
    reading. Why: parsing separate from calling, so it is tested on fixtures.

#### 25. `internal/github/errors.go` (Create)

*   **Proposed Changes**: maps `gh` exit code and stderr to `model.ErrorClass`
    (`(HTTP 401)`, rate-limit text, `(HTTP 502)`/`(HTTP 504)`, `gh` not found,
    unknown -> generic with last stderr line). Why: decision 0009.

#### 26. `internal/github/*_test.go`, `internal/github/testdata/*.json` (Create)

*   **Proposed Changes**: parse tests on scrubbed recorded outputs; error
    mapping tests that pin the stderr strings; query variable tests (no value
    ever appears in query text).

### GitHub Actions

#### 27. `internal/actions/provider.go` (Create)

*   **Proposed Changes**: `ActionsProvider` interface: `Runs(ctx, pr)`,
    `Jobs(ctx, run)` (jobs with steps and conclusions), `RerunFailed(ctx,
    run)`; `gh` implementation using REST through `gh api` (and `-i` where the
    budget headers matter); run id from `run_id.graphql` on demand. Details in
    `services/github-actions.md`.

#### 28. `internal/actions/*_test.go`, `internal/actions/testdata/*.json` (Create)

*   **Proposed Changes**: runs and jobs parsing; re-run refused on a run still
    in progress; failed-step extraction.

### Jenkins

#### 29. `internal/jenkins/url.go` (Create)

*   **Proposed Changes**: `Match(checkURL) -> Job, ok`: parse URL, require
    `https`, exact host from config, path against the configured job pattern,
    rebuild the job URL from parsed parts. Why: the token goes only to trusted
    URLs.

#### 30. `internal/jenkins/client.go` (Create)

*   **Proposed Changes**: HTTP client with Basic auth (user from config/env,
    token from `JENKINS_TOKEN`), timeout, concurrency cap; `LastBuild(ctx,
    job)`; `BuildNow(ctx, job, preset)` with queue follow (bounded tries) and
    one crumb retry; error classes (403 without `x-jenkins` -> network
    blocked; 401 -> auth expired; 404 -> not found, silent). Details in
    `services/jenkins.md`.

#### 31. `internal/jenkins/*_test.go` (Create)

*   **Proposed Changes**: `Match` with look-alike hosts (`ci.example.com.evil.io`),
    `http`, wrong path; client against a local test HTTP server: build states,
    403 with and without `x-jenkins`, queue follow, crumb retry, token never in
    logs.

### Tracker (Jira)

#### 32. `internal/tracker/tracker.go` (Create)

*   **Proposed Changes**: `Tracker` interface: `Keys(row)`, `Fetch(ctx,
    keys)`, `Transitions(ctx, key)`, `Move(ctx, key, quickMove)`, `URL(key)`.
    Key extraction: title, then branch, then body; case-insensitive; stored in
    upper case; first key is primary.

#### 33. `internal/tracker/jira/twg.go` (Create)

*   **Proposed Changes**: `twg` implementation through `proc.Runner`: one query
    for all keys, transitions list (read-only), move only when exactly one
    transition matches the quick move, key validation before any call, auth
    error -> "run `twg login --force`". Details in `services/jira-twg.md`.

#### 34. `internal/tracker/jira/*_test.go`, `testdata/*.json` (Create)

*   **Proposed Changes**: key extraction cases (lowercase branch, key mid
    title, no key), 0/1/2 matching transitions, auth error mapping.

### Core

#### 35. `internal/health/check.go` (Create)

*   **Proposed Changes**: availability checks: `gh` present, version at least
    the minimum, logged in; `twg` present and logged in; `JENKINS_TOKEN` set
    and host answers with `x-jenkins`. Used at start, on `r`, and by
    `ghtop doctor`. Why: decision #16 (optional sources).

#### 36. `internal/refresh/scheduler.go` (Create)

*   **Proposed Changes**: one 5-minute timer and manual trigger; per tick
    starts GitHub search for the active view, the review-requested count, and
    Jira/Jenkins refresh for known keys and jobs; skips a source already in
    flight; skips scheduled (not manual) GitHub polls below the budget floor.
    Returns Bubble Tea commands; never touches the UI directly.

#### 37. `internal/actionrun/runner.go` (Create)

*   **Proposed Changes**: action catalog (open PR, open ticket, open Jenkins
    build, re-run failed, update branch, Build Now, quick move): target
    captured at key press, confirm text, preconditions (for example update
    branch only when "behind" and no conflicts; nothing when unknown), one
    action per target at a time, audit line in the debug log, result message.
    Details in `core/actions.md`.

#### 38. `internal/debuglog/log.go` (Create)

*   **Proposed Changes**: `slog` file logger at
    `$XDG_STATE_HOME/ghtop/ghtop.log` (or `~/.local/state/ghtop/`), enabled by
    `--debug`; redacts `Authorization` headers and anything matching the token
    value. Why: diagnose failures without leaking secrets.

### UI

#### 39. `internal/ui/app.go` (Create)

*   **Proposed Changes**: root Bubble Tea model: active view, row store,
    source states, dialogs; the single update function that merges every
    result message; view switch (cached rows first, then refresh).

#### 40. `internal/ui/keys.go` (Create)

*   **Proposed Changes**: the keymap (arrows and `j/k`, `Enter`, `Esc`, `o`,
    `t`, `b`, `a`, `r`, `Ctrl-A` action menu, `/`, `:`, `?`, `q`, view keys);
    also feeds the help screen and README key list. Details in
    `core/keymap.md`.

#### 41. `internal/ui/table.go` (Create)

*   **Proposed Changes**: the shared PR table: columns, single-width glyphs,
    running mark, stale mark, column drop order below 120 and 80 columns,
    cursor by `PRID`, `/` filter.

#### 42. `internal/ui/header.go`, `internal/ui/statusbar.go`, `internal/ui/help.go` (Create)

*   **Proposed Changes**: header with view name, per-source state and age,
    GitHub budget left, review-requested count, running builds count; status
    bar with last action result and hints; help overlay from the keymap.

#### 43. `internal/ui/detail.go` (Create)

*   **Proposed Changes**: PR detail view: checks grouped by kind, tickets,
    per-item actions. Details in `views/pr-detail.md`.

#### 44. `internal/ui/actionsview.go` (Create)

*   **Proposed Changes**: `a` view: runs, jobs, failed steps, re-run, open in
    browser. Details in `views/actions-run.md`.

#### 45. `internal/ui/picker.go`, `internal/ui/confirm.go` (Create)

*   **Proposed Changes**: picker for several Jenkins jobs and presets;
    k9s-style confirm dialog (Cancel selected by default, names action and
    target).

#### 46. `internal/ui/styles.go` (Create)

*   **Proposed Changes**: glyph table and colors in one place.

#### 47. `internal/ui/*_test.go`, `internal/ui/testdata/*.golden` (Create)

*   **Proposed Changes**: render snapshots at 120 and 80 columns from fixture
    rows; key handling tests (cursor stays on PR after re-sort, confirm
    defaults to Cancel, update branch does nothing when state is unknown).

### Docs

#### 48. `docs/architecture.md` (Modify)

*   **Proposed Changes**: replace provider names with package paths once code
    exists; add the action sequence diagram (re-run with confirm). Why: kept in
    step with code (decision 0008).

#### 49. `docs/decisions/README.md` and `0001`-`0008` (Create)

*   **Proposed Changes**: index and the approved decision records from
    [CHECKLIST.md](./CHECKLIST.md). `0009` exists.

#### 50. `docs/ghtop-go.md`, `docs/ghtop-python-mvp.md` (Move -> `docs/archive/`)

*   **Proposed Changes**: moved unedited with a "superseded" line on top.

#### 51. `docs/plan/*` (Modify)

*   **Proposed Changes**: the design doc is saved at
    `docs/designs/ghtop.md`; spec files fill in per the checklist.

### Spike

#### 52. `spike/` (Create, then delete before M1)

*   **Proposed Changes**: a separate `main` package for M0, plus
    `spike/README.md` with findings. Deleted once M1 starts; the findings move
    into the spec files. Why: learn Bubble Tea focus, resize and refresh
    behavior before the real code.

## Verification Plan

*   **Compilation/Build**: `make build` (`go build ./...`).
*   **Unit Tests**: `make test` (`go test -race ./...`); fake runner and local
    HTTP server only; no test reaches GitHub, Jira or Jenkins.
*   **Static Analysis & Linting**: `make lint` (`go vet`, `golangci-lint` with
    the config above).
*   **Test Coverage Requirement**: 80% line coverage for `internal/model`,
    `internal/config`, `internal/jenkins`, `internal/github`,
    `internal/tracker`; UI packages covered by snapshots and key tests, no
    percentage target.
*   **Manual smoke**: `make smoke` runs the closed `gh` command list with my
    private config and prints each result shape; `ghtop doctor` shows all
    sources `ok` on VPN and Jenkins `VPN off?` without it.
*   **Leak check**: `make leakcheck` returns no hits over the whole tree before
    each push.
*   **Budget check**: with `--debug`, one hour of normal use logs at most 1500
    GraphQL points.
*   **CUJs**: each CUJ in the design doc walked through by hand at the end of
    the milestone that enables it.

## Decisions still needed before coding

These change what files 22, 37 and 40 contain. Each is settled in the session
named in [TASKS.md](./TASKS.md).

*   Merged view filter: `merged:>=` or `updated:>=`.
