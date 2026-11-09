# ghtop: detailed implementation plan

*   **Status:** Reviewed 2026-11-09 (Goldfish Stage 9, 2 rounds; M1 section still to write; see
    [2026-11-09-decisions.md](../reviews/2026-11-09-decisions.md))
*   **Design doc:** [ghtop.md](../designs/ghtop.md)
*   **Architecture:** [architecture.md](../architecture.md)

Every file the first version creates, changes or deletes, with what it holds
and, where it is not obvious, why. No code here. ghtop is a personal tool: one user, macOS and Linux, no
CI. The plan keeps the structure and the rules that protect against the
first attempt's failures (UI freezes, lost focus) and against leaking
organization data into the public repo.

Target paths are relative to the repo root; spec links are relative to
`docs/plan/`.

## Before coding starts

Before M1: write `services/github.md` (every `gh` and `twg` command ghtop runs,
with placeholders) and finish `config.md` (every key with type and default).
Other detail is written per milestone: a short section in this file, or the
agent's task prompt, right before that milestone starts.

## Starting point

The repo `go-dima/ghtop` has only docs. On `main`: `ghtop.md`,
`docs/ghtop-go.md`, `docs/ghtop-python-mvp.md`, `docs/python-alternative.md`.
The planning files are on branch `feat/v2`. The Python attempt lives on the
remote branch `feat/python-mvp` and is left untouched (not merged, not
deleted).

## Libraries

| Library | Use | Why this one |
|---|---|---|
| Bubble Tea | update loop, messages, commands | decided stack |
| Bubbles | table, viewport, key bindings, help | same family |
| Lip Gloss | styles, layout, width math | same family |
| `github.com/BurntSushi/toml` | config | reports unknown keys (`MetaData.Undecoded`), so typos in config are reported as errors |
| standard library only for everything else | `os/exec`, `net/http`, `regexp`, `log/slog`, `encoding/json`, `embed`, `runtime/debug` | fewer dependencies to update |

Use the latest major version of each library, with import paths as Charm
publishes them (check when `go.mod` is created). gh-dash is a source of ideas
only; ghtop does not follow its versions or code. Go: the current stable
release, recorded in `go.mod`. Written against `gh` 2.103.3 and `twg` 1.3.8
(installed 2026-11-08; informational, no version check at run time).

## Milestones

Each milestone ends with a working binary, passing tests, and its CUJs walked
through by hand.

| # | Milestone | Ends with |
|---|---|---|
| M1 | Read-only GitHub + framework check | config, `gh` runner, all four views, behind-by for open PRs, header (source state, remaining GitHub budget, review-requested count), status bar, help, `:` view commands and `:q`, `o`, pre-commit hooks, `--debug`, `--version`. **Exit check:** after a resize, columns reflow and the same PR stays selected; keys always reach the table, never swallowed by another widget; a refresh result arriving while the cursor moves keeps it on the same PR (or the file 14 fallback); input never blocks during a fetch (`j`/`k` respond while `gh` runs). |
| M2 | Jira + Jenkins state | key extraction, ticket column, `t`, Jenkins URL trust, last-build state, `b` (with job picker), availability flags, "VPN off?" hint |
| M3 | Detail + actions | PR detail view, Actions view (`a`), `Ctrl-A` action menu, confirm dialog, re-run failed, update branch, Jenkins Build Now, Jira quick move |

### Framework notes

Written during M1: what was learned about Bubble Tea focus, resize and
refresh handling, and the library versions chosen.

## M1 detail: the PR table

Settled 2026-11-09 from the mockups (placeholder data). The mockups show the
table as of M2; in M1 the `J` and `Ticket` columns are hidden and Title takes
their width.

### Columns

Left to right; the same table in every view.

| # | Column | Shows | Width at 120 | At 80 | From |
|---|---|---|---|---|---|
| 1 | (cursor) | `▸` on the selected row | 2 | 2 | UI |
| 2 | PR | `repo#N` (org left out: one org) | 14 | 14 | search |
| 3 | Title | as written (or key stripped, `ui.strip_key_from_title`), cut with `…` | rest | rest, min 20 | search |
| 4 | Author | login; Review-requested and Involved views only | 10 | dropped | search |
| 5 | Reviews | `✓N` approvals, `±N` changes requested (red) | 7 | 7 | reviews |
| 6 | Thr | `!N` unanswered review threads, `cN` unanswered conversation comments; `–` when both are 0 | 6 | 6 | threads, comments |
| 7 | A | worst GitHub Actions check state | 3 | 3 | check rollup |
| 8 | J | worst Jenkins check state (M2) | 3 | 3 | check rollup + `jenkins.Match` |
| 9 | State | see "State" below | 9 | 9 | search + compare |
| 10 | Ticket | primary key + status (M2) | 20 | key only (8) | Jira |
| 11 | Age | time since the PR's last update (`updatedAt`): `12m`, `5h`, `3d`, `6w` | 4 | dropped | search |

Shrink order as the terminal narrows below 120 columns: Title shrinks to 20;
then Age and Author drop; then the ticket status text drops (key stays); then
Thr drops. PR, Reviews, A, J and State never drop. Below the width that still
fits those, the table shows "terminal too narrow".

### State

One word, first match wins:

1. `draft`: `isDraft`.
2. `conflict`: `mergeStateStatus` is `DIRTY`.
3. `update`: behind the base (`behind_by` > 0 from the compare call, or
   `mergeStateStatus` `BEHIND`), no conflicts.
4. `ready`: the "ready" rule of file 14 (approved, CI ok, not `DIRTY`).
5. `–` otherwise.

Merged view: `merged` or `closed` (from `merged`).

### Reviews and threads

*   **Approvals / changes requested:** latest review per reviewer; count those
    whose latest state is `APPROVED` (`✓`) or `CHANGES_REQUESTED` (`±`, red).
*   **Unanswered review thread (`!`):** unresolved thread whose last comment
    is not by the viewer.
*   **Unanswered comment (`c`):** conversation comment (not a review thread)
    by another user after the viewer's last conversation comment (all of them
    if the viewer has none). Bot authors (`__typename` `Bot`) are not counted.
*   The viewer's login comes from `viewer { login }` in the same query.

### Sort and `s`

Two orders, toggled by `s`, the same in every view:

*   **Groups** (default): file 14 (CI failed, ready, rest; then ticket status
    order; then last commit, newest first).
*   **Last update:** `updatedAt`, newest first. GitHub's time: it moves on
    comments, pushes, labels and bot activity, not when only a CI run ends
    (concepts_brief.md section 7; the activity-time sort stays deferred).

The choice lasts for the session (not saved). The status bar names the
current order. The cursor stays on its PR across a toggle.

### Glyphs

All single-width. `ui.glyphs = "ascii"` swaps them:

| Meaning | unicode | ascii |
|---|---|---|
| passed / approvals | `✓` | `+` |
| failed | `✗` | `x` |
| running | `●` | `*` |
| no checks | `○` | `o` |
| none / not applicable | `–` | `-` |
| changes requested | `±` | `~` |
| unanswered thread / comment | `!` / `c` | `!` / `c` |
| cursor | `▸` | `>` |
| cut text | `…` | `~` |

Colors (in `styles.go`): passed and `ready` green; failed, `±` and
`conflict` red; running, `update` and unanswered counts amber; `merged`
purple; zero counts, `–`, `draft` and `closed` dim.

### Header and status bar

*   **Header:** `ghtop`, view tabs `1 Open`, `2 Merged`, `3 Review (N)` (N =
    review-requested count), `4 Involved`, then source state: `GH ok 42s rl
    4812/5000` (age of the last good fetch, GraphQL points left), plus `Jira`
    and `Jenkins` from M2. At 80 columns: shorter tabs and `GH✓ rl 4812`.
*   **Status bar:** row count, current sort, last action result or warning,
    and the main keys (`s o t b a ^A ?`).

### Row fields (`model.Row`, file 12)

`ID` (`owner/repo#N`), `Repo`, `Number`, `Title`, `URL`, `Author`,
`IsDraft`, `State` (open, merged, closed), `Base`, `Head`, `HeadSHA`,
`MergeState` (`mergeStateStatus`), `BehindBy`, `ReviewDecision`, `Approvals`,
`ChangesRequested`, `UnansweredThreads`, `UnansweredComments`, `Checks`
(name, kind, state, URL, app slug, workflow run id), `UpdatedAt`,
`LastCommitAt`, `Roles`; from M2 `Tickets` (key, status; first is primary).

### Query additions (file 20, `open.graphql`)

`isDraft`, `author { login }`, `updatedAt`, `viewer { login }`, and the PR's
conversation comments (`comments(last: 50) { author { login __typename }
createdAt }`). Check the cost against the G2 baseline (27 points for 9 PRs)
in the `--debug` log.

### Mockups

Open view, 120 columns, group sort:

```text
 ghtop   1 Open   2 Merged   3 Review (2)   4 Involved                      GH ok 42s rl 4812/5000  Jira ok  Jenkins ok

   PR             TITLE                                       REVIEWS THR    A   J   STATE     TICKET               AGE
▸  api#1412       Retry token refresh on 401 from the gateway ✓1 ±0   !2 c1  ✗   ✓   –         EX-482  In Progress    2h
   web#877        Add dark mode toggle to settings page       ✓2 ±0   –      ✓   ✓   ready     EX-470  Code Review    1d
   infra#233      Bump base image and pin node to 20.11       ✓0 ±0   !0 c2  ✓   ✓   update    EX-455  Code Review    3d
   api#1398       Split billing webhooks into their own work… ✓1 ±1   !1 c0  ✓   ✓   conflict  EX-441  Code Review    5d
   billing#55     Invoice export: CSV with tax columns        ✓0 ±0   –      ●   ●   –         EX-490  In Progress   12m
   api#1420       WIP: cache org settings per request         ✓0 ±0   –      ○   –   draft     EX-493  In Progress   40m

 6 PRs · sort: CI failed → ready → rest                    s sort  o open  t ticket  b build  a actions  ^A act  ? help
```

Review-requested view, 120 columns:

```text
 ghtop   1 Open   2 Merged   3 Review (2)   4 Involved                      GH ok 42s rl 4812/5000  Jira ok  Jenkins ok

   PR             TITLE                            AUTHOR     REVIEWS THR    A   J   STATE     TICKET               AGE
▸  api#1425       Rate limit per API key instead … alice      ✓0 ±0   !0 c1  ✓   ✓   –         EX-501  Code Review    3h
   web#880        Table virtualisation for the au… bob        ✓1 ±0   –      ●   –   update    EX-498  Code Review    1d





 2 PRs · sort: CI failed → ready → rest                    s sort  o open  t ticket  b build  a actions  ^A act  ? help
```

Open view, 80 columns:

```text
 ghtop   1 Open   2 Merged   3 Review·2   4 Inv      GH✓ Jira✓ Jenkins✓ rl 4812

   PR             TITLE                REVIEWS THR    A   J   STATE     TICKET
▸  api#1412       Retry token refresh… ✓1 ±0   !2 c1  ✗   ✓   –         EX-482
   web#877        Add dark mode toggl… ✓2 ±0   –      ✓   ✓   ready     EX-470
   infra#233      Bump base image and… ✓0 ±0   !0 c2  ✓   ✓   update    EX-455
   api#1398       Split billing webho… ✓1 ±1   !1 c0  ✓   ✓   conflict  EX-441
   billing#55     Invoice export: CSV… ✓0 ±0   –      ●   ●   –         EX-490
   api#1420       WIP: cache org sett… ✓0 ±0   –      ○   –   draft     EX-493

 6 PRs · sort: groups                                            s o t b a ^A ?
```

## Constants

Named constants in their packages, not config.

| Constant | Value | Package |
|---|---|---|
| `gh`/`twg` processes at once | 4 | `proc` |
| `gh`/`twg` timeout per call | 30 s | `proc` |
| Jenkins requests at once | 4 (own cap, separate from `proc`) | `jenkins` |
| Jenkins timeout per request | 10 s | `jenkins` |
| Build Now queue checks | at 10 s and 20 s after the POST | `jenkins` |

## Target files

### Repo root

#### 1. `go.mod`, `go.sum` (Create)

*   **Type / Scope**: Go module.
*   **Proposed Changes**: module `github.com/go-dima/ghtop`; the libraries
    above. Why: required for a Go build.

#### 2. `cmd/ghtop/main.go` (Create)

*   **Type / Scope**: entry point.
*   **Proposed Changes**: parses flags (`--config <path>`, `--debug`,
    `--version`); `--version` prints the module version from
    `runtime/debug.ReadBuildInfo` (when it is `(devel)`, the short
    `vcs.revision` plus `-dirty` if `vcs.modified`); loads config; builds the clients (gh runner,
    Jira, Jenkins) and hands them to the UI; on a config error exits non-zero
    with a message naming the config path and the failing key. Why: one place
    that wires everything, so packages do not build their own dependencies.

#### 3. `config.example.toml` (Create)

*   **Type / Scope**: sample config, placeholders only.
*   **Proposed Changes**: the TOML example from [config.md](./config.md), every
    key commented. Why: first run with no config prints its path and points
    here.

#### 4. `README.md` (Create)

*   **Type / Scope**: user docs.
*   **Proposed Changes**: what ghtop is, prerequisites (`gh` logged in; `twg`
    and `JENKINS_TOKEN` optional), install (`go install ./cmd/ghtop`), config
    path, contributor setup (`pre-commit install --hook-type pre-commit
    --hook-type pre-push --hook-type commit-msg`, private denylist path), key list (generated from
    the keymap, see file 37), link to `docs/`. Why: the repo has no README.

#### 5. `.gitignore` (Create)

*   **Proposed Changes**: build output, `dist/`, local config copies
    (`*.local.toml`), debug logs, EGM review reports in the repo root
    (`*_report*.md`, `overengineering_review.md`; already in the file). Why:
    keep binaries and private files out of git.

#### 6. `.pre-commit-config.yaml` (Create)

*   **Type / Scope**: local checks and leak guard (there is no CI).
*   **Proposed Changes**: hooks from `pre-commit/pre-commit-hooks` (pinned
    tag; check the current one when writing the file): `check-merge-conflict`,
    `check-added-large-files`, `detect-private-key`, `end-of-file-fixer`,
    `trailing-whitespace`. Local hooks: `gofmt -l -w` on Go files; `go vet
    ./...`; `golangci-lint` (config file 7); `go test ./...` at the
    `pre-push` stage; leak guard: `grep -nFi` of the staged text files
    against the private denylist `~/.config/ghtop/leakguard.txt` (org name,
    Jira site, key prefix, Jenkins host, user name), skipped with a warning
    when the denylist is missing. The same check runs at the `commit-msg`
    stage on the commit message. Blank denylist lines are skipped (an empty
    `-F` pattern matches everything); the denylist holds private values only,
    never the public GitHub user (it is in `go.mod` and every import); the
    hook sets `verbose: true` so the skip warning shows. Why: the repo is
    public and the private values cannot be listed in it;
    `pre-commit run --all-files` scans the whole tree.

#### 7. `.golangci.yml` (Create)

*   **Proposed Changes**: golangci-lint v2 config (`version: "2"`), default
    linters (`errcheck` is one of them) plus `gosec` (flags `exec.Command`
    with non-constant names and weak TLS). The runner's one
    `exec.CommandContext` line carries `//nolint:gosec // G204: closed
    command list` (file 16). Why: catches the mistakes the design rules
    forbid (shell use, ignored errors).

#### 8. `.github/pull_request_template.md` (Create)

*   **Proposed Changes**: checklist: "docs/architecture.md updated if the
    structure or a flow changed"; "decision recorded in
    docs/plan/concepts_brief.md if one was made". Why: agents open most PRs;
    the template reminds them to keep diagrams and decisions in step with the
    code.

#### 9. `LICENSE` (Create)

*   **Proposed Changes**: MIT. Why: the repo is public and has no license.

### Config

#### 10. `internal/config/config.go` (Create)

*   **Type / Scope**: config types and loading.
*   **Proposed Changes**: types for `[github]`, `[tracker]`, `[jenkins]`,
    `[ui]` exactly as [config.md](./config.md) defines them; path is
    `--config`, else `~/.config/ghtop/config.toml`; unknown keys -> error
    listing them; validation (org required, regexes compile, hosts have no
    scheme, durations parse, `ui.refresh` >= 1m, `*_days` >= 1, no duplicate
    quick-move `from`, `jenkins.user` or `JENKINS_USER` set when Jenkins is
    enabled, required keys of an enabled source present).
    Never writes the file. Why: one place that turns the file into checked
    values; no silent defaults that widen the search.

#### 11. `internal/config/config_test.go`, `internal/config/testdata/*.toml` (Create)

*   **Proposed Changes**: cases: valid full, minimal (GitHub only), missing
    org, bad regex, unknown key, refresh below 1m. Placeholders only.

### Model

#### 12. `internal/model/row.go` (Create)

*   **Type / Scope**: shared data types.
*   **Proposed Changes**: `PRID` (`owner/repo#N`), `Row`, `Check`, `Ticket`,
    `MergeState`, `CIState` with the worst-first order and `Worst()`, `Roles`;
    title kept as written, plus `DisplayTitle(stripLeadingKey bool)`. Fields
    as listed in "M1 detail: the PR table" above. Why:
    clients fill these, the UI reads them; no client types leak into the UI.

#### 13. `internal/model/source.go` (Create)

*   **Proposed Changes**: `Source` (GitHub, Actions, Jira, Jenkins),
    `SourceState` (available, last ok, last error, stale), and three fix hints:
    auth expired (`gh auth login` / `twg login --force`), "VPN off?" (Jenkins
    403 without `x-jenkins`), rate limited (with reset time). Any other error
    shows its last stderr line or HTTP status. A cap hit or a partial GraphQL
    error (`data` with `errors`) is a warning on a successful fetch, shown in
    the status bar. Why: one place for header,
    status bar and log wording.

#### 14. `internal/model/store.go` (Create)

*   **Proposed Changes**: row store keyed by `PRID` per view; every result
    message carries its view id and is merged only into that view's cache;
    merge functions per source (GitHub rows replace; Jira and Jenkins fill
    fields); sort, the same in every view: (1) CI failed, (2) ready (not
    draft; `reviewDecision` is `APPROVED`, or, when GitHub returns no
    `reviewDecision`, at least one approval and no changes requested; CI ok;
    `mergeStateStatus` not `DIRTY`), (3) the rest, including running CI;
    within each group by primary ticket status in `tracker.status_order`
    order (statuses not in the list and rows without a ticket last), then by
    last commit, newest first. CI state -> group: `failure` and `unstable` ->
    (1) CI failed; `success`, or a PR with no checks at all -> CI ok (needed
    for (2)); `running`, `aborted`, `unknown` -> (3). Cursor anchored by
    `PRID`; if that PR is no longer in the view (merged, closed, filtered,
    dropped from Review-requested), the cursor keeps the same row index,
    clamped to the last row (empty view: no selection). Pure functions, no
    I/O. Why: the sort and merge rules are testable without a terminal.

#### 15. `internal/model/store_test.go` (Create)

*   **Proposed Changes**: worst-state order, the sort groups above and the CI
    state -> group mapping, merge of partial results, cursor stays on the
    same PR after re-sort, cursor fallback when the PR leaves the view (same
    index, clamped; empty view), title strip only at the start, and the
    third M1 exit check at model level (a refresh result merged while the
    cursor moves keeps the cursor on its PR, or the fallback above).

### Process runner

#### 16. `internal/proc/runner.go` (Create)

*   **Type / Scope**: the only code that starts processes.
*   **Proposed Changes**: `Runner` interface, the one interface in ghtop,
    with two methods:
    *   `Run(ctx, name, args) -> stdout, stderr, exit code` for `gh` and
        `twg` (no stdin): argument list only (no shell), fixed env additions
        (`GH_PROMPT_DISABLED=1`, `GH_PAGER=`, `NO_COLOR=1`), timeout per call
        and a cap on processes running at once (see Constants), cancel on
        context, debug-log line per call (name, args with query text replaced
        by the query file name, duration, exit code; args hold org name,
        search text and JQL, never tokens).
    *   `Start(name, args) -> error` for fire-and-forget processes (the
        browser opener used by `o`, `t`, `b`): argument list only, stdout and
        stderr go to `/dev/null`, `cmd.WaitDelay` is set so a forked child
        holding pipes cannot block, does not count against the process cap.
        Only a failure to start is reported (status bar).
    `Run` and `Start` share one command-building helper, so there is one
    `exec.CommandContext` line; it carries one justified
    `//nolint:gosec // G204: closed command list`; without it the
    golangci-lint hook (file 7) blocks this file. Why: one audited place for
    subprocess rules (concepts_brief.md, "GitHub access").

#### 17. `internal/proc/fake.go`, `internal/proc/runner_test.go` (Create)

*   **Proposed Changes**: a fake runner that returns recorded outputs by
    command and records `Start` calls; tests for timeout and cancel.

### GitHub

#### 18. `internal/github/client.go` (Create)

*   **Proposed Changes**: concrete `Client` with domain-level methods:
    `Search(ctx, view) -> rows, rateLimit{remaining, resetAt}, warnings`,
    `ReviewRequestedCount(ctx)`, `BehindBy(ctx, rows)`, `UpdateBranch(ctx,
    pr)`; calls `proc.Runner`. `BehindBy` runs one REST compare per open PR
    (`behind_by`), after each Open, Involved or Review-requested search, for
    the active view's open PRs only (never Merged), through `Run` and the
    process cap. Conflicts still come from `mergeStateStatus` (`DIRTY`).
    Compare calls use the separate REST core quota (5000/hour); at a 5 min
    refresh this is far below the limit, so it is not shown in the header.
    Callers never see `gh` arguments or output. Why: a later switch to `go-gh`
    rewrites `internal/github` and `internal/actions` only.

#### 19. `internal/github/commands.go` (Create)

*   **Proposed Changes**: the closed list of `gh` commands ghtop runs, one
    named entry each (for example "search open PRs": `gh api graphql -f
    query=<embedded open.graphql> -f q=...`), matching
    [services/github.md](./services/github.md). Merged view search uses
    `is:closed updated:>=<date>`, so it also shows PRs closed without merging;
    the state column tells them apart. "compare base...head per PR": `gh api
    repos/<owner>/<repo>/compare/<base>...<head>`, reading `behind_by`; owner,
    repo, base and head come from the PR row, and ghtop builds the path
    segments itself (no `{owner}`/`{repo}` placeholders): each segment is
    path-escaped, with `/` inside branch names kept (git ref rules already
    forbid `..`, spaces and `~^:?*[`). The call is a plain GET with no `-f`
    fields, which would switch `gh api` to POST. `-f` (raw string) for every
    string value; `-F` only for numbers and booleans that ghtop itself
    produces. Why: no command is built anywhere else; `-F` reads a file when
    the value starts with `@`, converts true/false/null/numbers, and fills
    `{owner}`/`{repo}`/`{branch}`, while branch names and titles from other
    people's PRs are untrusted.

#### 20. `internal/github/queries/{open,closed,count,run_id}.graphql` (Create)

*   **Proposed Changes**: `open.graphql` (full: reviews, `reviewDecision`,
    threads, comments, checks, `mergeStateStatus`), `closed.graphql` (light:
    `state`, `merged`, `mergedAt`, `closedAt`, reviews, rollup state),
    `count.graphql` (`issueCount` only), `run_id.graphql` (check suite ->
    workflow run id). Behind-by is REST, not GraphQL (file 18). All take
    values as variables (strings passed with `-f`), all request
    `rateLimit { cost remaining resetAt }`.
    Embedded in the binary (`embed`) and passed inline as `-f query=<text>`.
    Why: queries reviewable as files; no values pasted into query text.

#### 21. `internal/github/parse.go` (Create)

*   **Proposed Changes**: JSON -> `model.Row`; check classification (M1:
    Actions by app slug, everything else "other"; M2 adds Jenkins via
    `jenkins.Match`); cap warnings; rate-limit
    reading for the header. Why: parsing kept separate from calling. No parse
    tests (cut 5 keeps tests to the listed pure logic).

#### 22. `internal/github/errors.go` (Create)

*   **Proposed Changes**: maps `gh` exit code and stderr to the three hints
    (`(HTTP 401)`/"gh auth login" -> auth expired; rate-limit text -> rate
    limited) or to "other" with the last stderr line. Partial GraphQL errors:
    `gh api graphql` exits non-zero when the response has `errors` even when
    `data` is present (for example one repo behind SAML/SSO, one node
    timeout). If stdout has `data`, it is parsed, the rows are shown, and the
    `errors` messages become a status-bar warning (source stays ok); the fetch
    fails (source stale, hint mapping) only when there is no `data`.

#### 23. `internal/github/errors_test.go`, `internal/github/testdata/*.json` (Create)

*   **Proposed Changes**: error mapping tests that pin the stderr strings
    behind the hints, plus one test for a partial GraphQL error (non-zero
    exit with `data` and `errors` -> rows plus warning) with one scrubbed
    fixture. Fixtures are scrubbed recorded outputs (placeholders
    only) used while writing the parser.

### GitHub Actions

#### 24. `internal/actions/client.go` (Create)

*   **Proposed Changes**: concrete `Client`: `Runs(ctx, pr)`, `Jobs(ctx, run)`
    (jobs with steps and conclusions), `RerunFailed(ctx, run)`; REST through
    `gh api`; run id from `run_id.graphql` on demand; re-run refused on a run
    still in progress. Detail written at M3.

### Jenkins

#### 25. `internal/jenkins/url.go` (Create)

*   **Proposed Changes**: `Match(checkURL) -> Job, ok`: parse URL, require
    `https`, exact host from config, path against the configured job pattern,
    rebuild the job URL from parsed parts. `QueueURL(job, location) -> url,
    ok`: parse only the queue item id from the `Location` path
    (`/queue/item/<id>/`) and build
    `https://<job's configured host>/queue/item/<id>/api/json`; the
    `Location` URL is never used as given (Jenkins builds it from its
    configured root, which may be `http://` or another host). Why: the token
    goes only to trusted URLs.

#### 26. `internal/jenkins/client.go` (Create)

*   **Proposed Changes**: concrete `Client`: HTTP with Basic auth (user from
    config or `JENKINS_USER`, token from `JENKINS_TOKEN`), timeout and its own
    request cap (see Constants); `LastBuild(ctx, job)`; `BuildNow(ctx, job)`:
    first `GET <job>/api/json?tree=property[parameterDefinitions[name]]`; if
    the job has parameters, POST `buildWithParameters` with none (the job uses
    its defaults), otherwise POST `/build`; then takes the queue item id from
    the `Location` header, polls the queue URL built by file 25 at 10 s and
    20 s; if a build number appears the status bar shows it with a link,
    otherwise "queued" and the next refresh picks the build up. If no id
    parses, it reports "queued" and does not poll. Errors: 403 without
    `x-jenkins` -> "VPN off?"; 401 -> auth expired; 404 -> ignored,
    GitHub check state kept. The debug log records method, URL path and
    status, never headers or bodies. Detail written at M2/M3.

#### 27. `internal/jenkins/url_test.go` (Create)

*   **Proposed Changes**: `Match` with look-alike hosts
    (`ci.example.com.evil.io`), `http`, wrong path.

### Jira

#### 28. `internal/jira/keys.go` (Create)

*   **Proposed Changes**: `Keys(row)`: key extraction from title, then branch,
    then body; case-insensitive; stored in upper case; first key is primary.

#### 29. `internal/jira/client.go` (Create)

*   **Proposed Changes**: concrete `Client` through `proc.Runner`:
    `Fetch(ctx, keys)` (one query for all keys), `Transitions(ctx, key)`
    (read-only), `Move(ctx, key, quickMove)` only when exactly one transition
    matches, `URL(key)`; key validation before any call; auth error -> "run
    `twg login --force`". Commands as listed in `services/github.md`.

#### 30. `internal/jira/keys_test.go` (Create)

*   **Proposed Changes**: key extraction cases (lowercase branch, key mid
    title, no key, several keys).

### Core

#### 31. `internal/health/check.go` (Create)

*   **Proposed Changes**: availability checks at start and on `r`: `gh`
    logged in; `twg` present and logged in; `JENKINS_TOKEN` set and at least
    one configured Jenkins host answers (all hosts probed in parallel). Jenkins
    probe: `GET https://<host>/api/json?tree=mode` with Basic auth; 200 with
    `x-jenkins` -> available; 401/403 with `x-jenkins` -> auth expired; no
    response or no `x-jenkins` -> "VPN off?". The `gh` and `twg` probe
    commands are listed in `services/github.md`. Sets the per-source
    "available" flag. Why: concepts_brief.md
    item 16 (optional sources).

#### 32. `internal/refresh/scheduler.go` (Create)

*   **Proposed Changes**: one timer (`ui.refresh`, default 5 minutes) and the
    `r` trigger; per tick starts the GitHub search for the active view (then
    behind-by for its open PRs, not in Merged), the review-requested count,
    and Jira/Jenkins refresh for known keys and jobs. "In flight" is tracked
    per (source, view): a fetch is skipped only when the same source is
    already running for the same view, so switching views starts the new
    view's fetch at once. Leaving a view does not cancel its fetch (the result
    fills that view's cache); only quit cancels all running calls. Returns Bubble Tea commands; never
    touches the UI directly.

#### 33. `internal/actionrun/runner.go` (Create)

*   **Proposed Changes**: action catalog (re-run failed, update branch, Build
    Now, quick move): target captured at key press, confirm text,
    preconditions (for example update branch only when "behind" and no
    conflicts; nothing when unknown), one action per target at a time, audit
    line in the debug log, result message. Detail written at M3.

#### 34. `internal/debuglog/log.go` (Create)

*   **Proposed Changes**: `slog` file logger at
    `$XDG_STATE_HOME/ghtop/ghtop.log` (or `~/.local/state/ghtop/`), enabled by
    `--debug`. Callers log names, args, paths, durations and status codes;
    never HTTP headers, bodies or tokens. Args contain the org name, search
    text and JQL, so the log file is created with mode 0600 and its directory
    with 0700.

### Platform

#### 35. `internal/platform/open.go` (Create)

*   **Proposed Changes**: open a URL in the browser (`open` on macOS,
    `xdg-open` on Linux) through `proc.Runner.Start` (detached, so a slow
    or hanging opener never blocks the UI). Only URLs built from GitHub data,
    the configured Jira site, or trusted Jenkins URLs are opened.

### UI

#### 36. `internal/ui/app.go` (Create)

*   **Proposed Changes**: root Bubble Tea model: active view, row store,
    source states, dialogs; the single update function that merges every
    result message (stored in the cache of the view it is tagged with); view
    switch (cached rows first, then refresh; a fetch still running for the
    old view keeps going and fills its cache).

#### 37. `internal/ui/keys.go` (Create)

*   **Proposed Changes**: the keymap exactly as in
    [core/keymap.md](./core/keymap.md); also feeds the help screen and README
    key list.

#### 38. `internal/ui/menu.go`, `internal/ui/cmdline.go` (Create)

*   **Proposed Changes**: the `Ctrl-A` action menu (letters from the keymap;
    lists only actions whose precondition holds now) and the `:` command line
    (`:open`, `:merged`, `:review`, `:involved`, `:q`).

#### 39. `internal/ui/table.go` (Create)

*   **Proposed Changes**: the shared PR table as in "M1 detail: the PR
    table" above: columns, single-width glyphs, running mark, stale mark,
    shrink order, cursor by `PRID`, `/` filter, `s` sort toggle.

#### 40. `internal/ui/header.go`, `internal/ui/statusbar.go`, `internal/ui/help.go` (Create)

*   **Proposed Changes**: header with view name, per-source state and age,
    GitHub budget left, review-requested count, running builds count; status
    bar with last action result, warnings and hints; help overlay from the
    keymap.

#### 41. `internal/ui/detail.go` (Create)

*   **Proposed Changes**: PR detail view: checks grouped by kind, tickets,
    per-item actions. Detail written at M3.

#### 42. `internal/ui/actionsview.go` (Create)

*   **Proposed Changes**: `a` view: runs, jobs, failed steps, re-run, open in
    browser. Detail written at M3.

#### 43. `internal/ui/picker.go`, `internal/ui/confirm.go` (Create)

*   **Proposed Changes**: job picker for PRs with several Jenkins jobs;
    k9s-style confirm dialog (Cancel selected by default, names action and
    target).

#### 44. `internal/ui/styles.go` (Create)

*   **Proposed Changes**: glyph table and colors in one place.

### Docs

#### 45. `docs/plan/services/github.md` (Create, before M1)

*   **Proposed Changes**: every `gh` and `twg` command ghtop runs, with
    placeholders, so each can be copied and run by hand; the search query per
    view; caps.

#### 46. `docs/plan/config.md` (Modify, before M1)

*   **Proposed Changes**: every key with type and default; example and
    alternatives kept.

#### 47. `docs/architecture.md` (Modify)

*   **Proposed Changes**: kept in step with the code: package paths once code
    exists, the action sequence diagram (re-run with confirm). Why:
    concepts_brief.md item 15.

## Verification Plan

*   **Build**: `go build ./...`.
*   **Unit tests**: `go test ./...` (pre-push hook); fake runner only; no test
    reaches GitHub, Jira or Jenkins. Tests cover the pure logic that is easy
    to get wrong: store sort, merge and cursor anchoring; Jira key extraction;
    Jenkins `Match`; `gh` stderr -> hint mapping, including partial GraphQL
    errors; config validation; runner timeout and cancel.
*   **Static analysis**: `go vet` and `golangci-lint` (pre-commit hooks).
*   **Leak check**: `pre-commit run --all-files` returns no hits.
*   **Sources**: the header shows all sources `ok` on VPN and
    `Jenkins: VPN off?` without it.
*   **After a `gh` or `twg` upgrade**: run `ghtop --debug` and check the log
    for non-zero exits.
*   **CUJs**: each CUJ in the design doc walked through by hand at the end of
    the milestone that enables it.

## Decisions still needed

None. Behind-by was settled in the round 2 re-audit: one REST compare per open
PR, from M1 (files 18, 19).
