# ghtop

* **Author:** Dima Gonikman
* **Date:** 2026-11-08

## Overview

ghtop is a terminal app with k9s-style keyboard navigation. It shows the pull
requests of the user logged in to the `gh` CLI, one view at a time:

- **Open PRs** that I authored.
- **Merged PRs** from the last N days (default 14, set in config).
- **Review-requested PRs**: PRs by others where my review is
  requested now. Follows GitHub's behavior: once I submit a review, the PR
  leaves this view. In practice the view holds open PRs only.
- **Involved PRs**: PRs by others that involve me (gh-dash's
  "Involved" section, search `involves:@me -author:@me`; `involves` covers
  assignee, mention and commenter). Open PRs only, limited to the last 14 days
  (most such PRs are merged or closed before that). Closed PRs are hidden.
  Default filter: `updated:>=` 14 days ago, so a PR with recent activity stays
  even if it was opened earlier. Author: `updated` is the starting choice and
  may change later.

All views are the same PR table with a different data source (search query
and, where needed, lighter data for closed PRs). Every view shows the same
columns, including Jira, GitHub Actions and Jenkins: company policy puts
tickets and CI on every PR, including other people's.

Each row shows the PR state, the review state, CI state (GitHub Actions runs and
Jenkins builds, both found through the PR's checks) and the linked issue-tracker
ticket (Jira first, through the `twg` CLI). From the highlighted row the user can
open the PR, ticket or build in the browser, move the ticket to another status,
re-run a failed Actions run, start a Jenkins "Build Now" (with the job's default
parameters), and see why a run failed.

The target user is a developer who wants to track their own PRs from the
terminal. ghtop runs next to pr-tracker (a local web page with the same data). It
takes ideas from pr-tracker, not code.

Prerequisites: `gh` (logged in), `twg` (logged in) for Jira, `JENKINS_TOKEN` in
the environment for Jenkins. The repo is public, so all organization data lives
in a private user config file.

## Analysis

Six reviewers looked at the concept. Their findings, grouped and ranked.

### 1. The planning set can repeat the failure of the first attempt

The first attempt specified five screens, a log viewer and pinning in two long
plans (about 80% the same text) before any UI ran, and the UI ended up broken.
A plan with 10+ files repeats that pattern at a larger size. Likely causes of
the old UI bugs, seen in the old plans: the
framework's focus handling, one `gh run list` call per PR on a 10 s poll, and
refresh results arriving while the user moved the cursor. Reviewers suggest a
small UI spike (one table from one GraphQL call, `j/k`, `o`, `r`) early, so
real behavior feeds the plan.

### 2. Fast polling while CI runs can exhaust the GitHub quota

GitHub gives 5000 GraphQL points per hour per user. pr-tracker's full query for
open PRs costs about 26 points at its current caps, and about 105 points at
larger caps, plus one extra query for "behind base" counts. Polling that full
query every 15-30 s uses 3,000-13,000 points per hour. The budget is shared with
pr-tracker, the `gh` CLI and any other ghtop window.

The fix is two tiers of queries:

- **Slow tier:** the full search, every 5 minutes and on manual refresh.
- **Fast tier:** only the PRs with running checks, fetched by node id with the CI
  rollup only (about 1 point), plus Jenkins over its own REST API (no GitHub
  cost).

Every query reads `rateLimit { cost remaining resetAt }`. The fast tier stops on
its own when the remaining budget falls below a floor (for example 20%), and has
a maximum duration. Closed PRs keep the light query, because the full query for
them took over GitHub's 10 s limit and failed with HTTP 502/504.

### 3. Security: the Jenkins token can leak through a check URL

pr-tracker accepts a check URL as a Jenkins URL when it *contains* the Jenkins
host name. A host like `ci.example.com.attacker.io` passes that test, and anyone
who can post a commit status can set that URL. ghtop sends `JENKINS_TOKEN` to
these URLs. ghtop must parse the URL, require `https` and an exact host from
the private config, and build the API URL from the parsed parts. "Build Now" runs
only on job URLs that match a configured pattern, and its queue URL is rebuilt
from the configured host and the queue item id, never taken from `Location`.

### 4. Public repo: organization data leaks easily

pr-tracker has organization values in more places than its config file: the
title-cleanup regex, the key regex in the server, the Jenkins job naming rule
(`<repo>_<arch>`), the "ready to merge" rule (two approvals), the status names in
the sort order, the env file in `package.json`, and the guide text. Copying ideas
from it brings these values along. Rules for ghtop:

- Specs, mockups and test data use placeholders only (`example-org`, `EX-123`,
  `ci.example.com`).
- A local pre-commit check greps for the private values. The list comes from a
  private denylist file (`~/.config/ghtop/leakguard.txt`), so it is not in
  the repo.
- Logs and caches go to user directories, never the repo.

### 5. Keyboard UX problems

- **Wrong row after re-sort.** A "last updated" sort reorders rows on every poll.
  A key press can then act on a different PR than the one the user looked at. The
  cursor must follow the PR (`owner/repo#N`), the target is captured when the key
  is pressed, and the confirm dialog names the exact target.
- **`j` for Jira clashes with `j` = down** in vim and k9s. Use `t` (ticket). This
  also fits a tracker that is not always Jira. Reserved keys: `j k g G / : ? q Esc
  Enter`.
- **One row, many targets.** A PR can have several Jenkins jobs, several Actions
  runs and several ticket keys. The row cell shows a summary (worst state and
  counts). When an action has more than one target, ghtop shows a picker or opens
  the detail view.

### 6. gh-dash may already cover most of the need

gh-dash is a `gh` extension with PR sections built from search filters and
custom keys that run shell commands with the repo, PR number and branch. That can
cover open/merged views, re-run (`gh run rerun --failed`), opening the ticket,
moving it with `twg`, Jenkins Build Now through `curl`, and failed logs
(`gh run view --log-failed | less`). The gaps reviewers expect: no Jira status
column, no live Jenkins state, no custom sort. This is model knowledge and was
not checked. A 30-minute trial gives the answer; its gaps define what ghtop adds.

**Trial result (author):** gh-dash shows PR data well and its shortcuts work
well, but it has no Jira or Jenkins content and lacks the needed actions. Its PR
view fits a drill-down; the main need is an overview across PRs.

### 6b. Fork or rewrite

Points against a fork:

- The parts ghtop changes most (the overview table, the drill-down with
  actions, Jira and Jenkins data) are the parts a fork would rewrite. What stays
  untouched is the parts that are easy to write: the gh auth setup, the list
  widget, the help bar.
- gh-dash builds each section from its own search query. The author notes ghtop
  can use separate queries per view too, so the query shape is an
  implementation detail and not a reason against a fork. What remains: adding
  Jira and Jenkins data to every row, row actions, and the refresh rules
  changes gh-dash's row model and fetch code, which makes upstream updates
  manual merges.
- A fork that drifts from upstream ends as a rewrite with someone else's
  structure.

Points for a fork:

- A working drill-down PR view (description, checks, files, comments) on day
  one, and a keymap and help system that already behave well.
- Proven handling of terminal resize, focus and scrolling, which is where the
  first ghtop attempt broke.

Middle path: write a new tool on the same stack as gh-dash (Go, Bubble Tea),
copy its keymap conventions, and read its code as a reference for focus and
layout handling. Check its license before copying any code.

### 7. "Last updated" sort is not defined yet

The PR's `updatedAt` does not change when a Jenkins build or a check changes, and
it does change on bot comments and labels. A useful value is
`activityAt = max(PR updatedAt, last commit date, check start/end times, Jenkins
build end time)`. The check times are not in pr-tracker's query, so they add
cost. Times from CI changes are lost on restart unless stored. Open question:
does this sort replace pr-tracker's group sort (CI failed, then ready to merge,
then the rest) or apply inside each group?

### 8. Actions and Jenkins actions need data the current query lacks

- **Actions re-run** needs the workflow run id. pr-tracker's check data has no
  run id. Options: ask GraphQL for `checkSuite { app { slug } workflowRun {
  databaseId } }` (reliable, costs points; `github-actions` app slug also tells
  Actions apart from other apps), or parse `/actions/runs/<id>/` from the check
  URL (free, breaks if GitHub changes URLs). Recommendation: GraphQL, loaded only
  when the user opens the detail view. Re-run of failed jobs works only on
  completed runs and within 30 days.
- **Jenkins Build Now** is `POST <job>/build` or `POST <job>/buildWithParameters`.
  Jenkins answers with a queue item, not a build number, so ghtop must follow the
  queue item to find the new build. Parameter definitions come from the job's
  `api/json` and exist only after the first build of a multibranch PR job. A PR
  with no Jenkins check yet has no job URL to use: the job URL is built only
  from a check URL that matches the configured host and job pattern. No crumb
  (API token auth needs none). One in-flight trigger per job.

### 9. Jira transitions

Keep pr-tracker's guards: a quick move runs only when exactly one transition
matches, quick moves come from a config allowlist, and "Done" waits until the PR
is merged. Transitions that need fields (for example a resolution) fail; v1 shows
the error and offers to open the ticket. Every transition asks for confirmation.
Ticket keys are validated before they go into JQL or command arguments.

### 10. Errors and source health

A failed source must not blank the table. pr-tracker shows zero rows when GitHub
fails; ghtop keeps the old rows and marks them stale. Error classes and what the
user sees:

| Class | Example | Shown as |
|---|---|---|
| Tool missing | `gh` or `twg` not installed | install hint |
| Auth expired | `twg` login expired, Jenkins 401 | fix command (`twg login --force`) |
| Network blocked | Jenkins 403 with no `x-jenkins` header | "VPN off?", not "bad token" |
| Rate limited | GitHub primary or secondary limit | wait until `resetAt` |
| Upstream timeout | GitHub 502/504 | retry next poll, no tight loop |
| Not found | deleted Jenkins build (404) | silent, keep GitHub state |
| Truncated | more PRs than the cap | warning in the UI |
| Config invalid | bad or old config file | path and reason, no silent defaults |
| Action rejected | 0 or 2+ matching transitions | reason, nothing changed |

A header strip shows each source's age, state and fix hint, for example
`GH ok 42s rl 4812/5000 | Jenkins x VPN off? | Jira x twg login --force`.
A `--debug` log (tokens removed) and a `ghtop doctor` preflight command help
diagnose setup problems.

### 11. Config

The old plans used `~/.config/ghtop/config.yaml` with a repo-centric `pinned`
list. The new config needs a `version` field. An old or unknown version stops
ghtop with a hint; it never falls back to defaults, because defaults without an
org filter widen the search. ghtop never writes the config; UI state goes to a
separate state directory. On macOS the config path must be set explicitly
(several libraries default to `~/Library/Application Support`). Secrets come
from the environment only.

### 12. Pluggable tracker and CI: interfaces, not a plugin system

There is one tracker and two CI kinds. Small internal interfaces with one
implementation each, switched on in config, cover this:
`Tracker { ExtractKeys, Fetch, Transitions, Transition, URL }` and
`CIProvider { Match(check), Status, Trigger, Logs }`. Views read capability flags,
not provider names.

### Smaller points

- Emoji take two columns in many terminals and break alignment. Decision #23:
  single-width symbols only, no emoji.
- GitHub search can lag: a new PR may be missing for a few minutes.
- `twg` JSON output has no version; pin a minimum `twg` version and parse
  leniently.
- Do not source an interactive shell for env values (it hung pr-tracker).
- macOS has no `timeout` command; use in-process timeouts.
- Worst-state order: use pr-tracker's (failure > unstable > building > aborted >
  unknown > success), not the old plan's (running first).

## Goals vs. Non-Goals

* **In-Scope Goals (MVP):**
  * Four views on one shared PR table, one at a time: Open, Merged (last 14
    days), Review-requested (`review-requested:@me`; reviewed PRs drop out) and
    Involved (`involves:@me -author:@me`, open, updated in the last 14 days).
    Each view differs only in its query.
  * Columns: `repo#N`, PR state (draft, conflicts, behind), reviews, CI summary
    for Actions and Jenkins, ticket key and status.
  * Keys (full list in `core/keymap.md`): arrows and `j/k` to move, `1`-`4`
    views; `o` open PR, `t` open ticket, `b` Jenkins build in browser (picker
    if several), `a` Actions run view, `r` refresh, `?` help, `:` command,
    `/` filter, `Enter` detail. Every change goes through the `Ctrl-A` action
    menu, then confirm: `r` re-run failed jobs, `b` Jenkins Build Now, `u`
    update branch, `m` Jira quick move.
  * Actions run view (`a`): the PR's workflow runs, their jobs and state, and
    the failed steps, fetched on open; open in browser as a second step.
  * Update branch: merge the base branch into the PR branch when it is behind
    and has no conflicts; with conflicts, open the PR page; no action while
    GitHub has not computed the state. Merge only (rebase deferred).
  * Refresh every 5 minutes plus manual, active view only; Review-requested
    count in the background.
  * Source health strip and stale-data marking.
  * Private config; placeholder-only public repo.
* **In-Scope, later phases:**
  * Fast Jenkins poll while builds run.
  * Jenkins Build Now with parameters (v1: Build Now with the job's default
    parameters).
  * "Last updated" activity sort.
  * In-app log viewer. The first version shows failed jobs and steps in the
    Actions run view and opens full logs in the browser.
* **Out-of-Scope Non-Goals:**
  * Org -> repo -> PR browsing and per-PR `gh run list` calls.
  * A general Jenkins job browser (raycast-jenkins-commander covers it).
  * A plugin system for trackers or CI.
  * Changed-row highlighting and ack (pr-tracker feature).
  * Multi-org, Windows, sharing code with pr-tracker.

## Alternatives Weighed

* **gh-dash config plus private scripts.** Rejected by author after a trial:
  gh-dash shows PR data well, but has no Jira or Jenkins content and lacks the
  needed actions. Its PR view fits the drill-down role, but the main need is an
  overview across PRs. Kept from gh-dash: its keyboard shortcuts, as the model
  for ghtop's keymap.
* **Fork gh-dash.** Rejected by author: the fork would rewrite the parts that
  matter (overview, actions, Jira and Jenkins data) and then carry upstream
  merges. Chosen instead: a new tool on the same stack (Go + Bubble Tea) that
  borrows gh-dash's keymap ideas and reads its code as a reference.
* **Arrow keys only (no vim keys).** Considered, then dropped by author: once
  the ticket key became `t`, `j/k` no longer clash, so both are kept.
* **Fast polling of GitHub while CI runs.** Rejected by author for now: fast
  polling is deferred, and when added it polls Jenkins, which has no GitHub
  budget cost.
* **TUI over pr-tracker's HTTP API (`/api/rows`, `/api/jira/*`).** Least code and
  reuses its data handling. Rejected by author: ghtop is a separate tool that
  shares ideas, not implementation, and should not need the pr-tracker server.
* **pr-tracker `--tui` mode.** Rejected by reviewers: pr-tracker uses Node with no
  packages, which makes a TUI hard; also against the separate-tool decision.
* **Repo-centric hierarchy from the first attempt.** Rejected by author: the
  user-centric search finds my PRs across the org in one query and avoids
  per-repo calls.
* **Changed-row highlighting.** Rejected by author: a "last updated" sort covers
  the need.
* **Standalone ghtop with one GraphQL search (baseline).** Kept. Stack is open;
  reviewers lean to a Go `gh` extension (token from `gh` in-process, single
  binary, `gh ghtop` install) with Bubble Tea or tview.

## Key Decisions & Staging for Next Steps

Decided:

1. User-centric views: Open, Merged (N days), Review-requested later.
2. Separate tool from pr-tracker; ideas only.
3. Jira through `twg`; Jenkins optional; Actions first.
4. Jenkins actions limited to Build Now, sometimes with parameters.
5. Refresh like pr-tracker plus manual, plus an optional faster poll while CI
   runs.
6. All organization data private; public repo holds generic defaults only.
7. Row actions: flat row with keys plus a drill-down detail view, final choice
   after mockups.
8. New tool, not a gh-dash fork, on gh-dash's stack (Go + Bubble Tea). gh-dash
   code is a reference for focus, layout and keymap handling.
9. Navigation with arrow keys and vim `j/k` (no clash: the ticket key is
   `t`, not `j`). Fixed so far: `t` = ticket, `b` = Jenkins build (opens
   in browser), `a` = Actions run drill-down (jobs and steps in ghtop), `r` =
   refresh. The re-run key is still open. The rest of the
   keymap is designed key by key in `core/keymap.md`.
10. Fast polling is deferred. When added, it polls Jenkins for running builds,
    not GitHub.
11. A small UI spike runs after the mockups and before the behavior specs.
12. Views: Open, Merged, Review-requested and Involved are four separate views,
    all in the first phase, on one shared PR table; each view only defines its data source. Same
    columns everywhere (Jira and CI are on every PR by company policy).
    Merged shows my PRs closed in the last 14 days. Involved shows open PRs
    from the last 14 days only. Review-requested follows GitHub
    (reviewed PRs drop out).
13. Fetching: only the view on screen is fetched and polled. Review-requested
    is the exception: a count-only query runs in the background and feeds a
    count in the header; its rows are fetched when the user switches to it.
    On every view switch, ghtop shows the cached rows (marked with their age)
    right away and refreshes in the background. A fetch started before
    leaving a view still completes into its cache; only the view on screen
    is polled.
14. Planning set: reduced in the 2026-11-09 review (item 27) to the design
    doc, `implementation.md`, `core/keymap.md`, `config.md` and
    `services/github.md`; other detail is written per milestone.
15. Process: every decision is recorded in this file (this list, or a section
    like "GitHub access" below), and `docs/architecture.md` keeps Mermaid
    diagrams and flows of the system, updated in the same change as the code.
    The PR template reminds agents of both.

16. Jira and Jenkins are optional. On start, ghtop checks each source (Jira:
    `twg` installed and logged in; Jenkins: `JENKINS_TOKEN` set and the host
    answers with an `x-jenkins` header) and sets an "available" flag per
    source. Manual refresh runs the check again. A source without access still
    gets links (ticket URL from the key and the configured Jira site; build URL
    from the GitHub check), but no data is pulled from it.
17. One poll interval: every 5 minutes, plus `r`. No faster GitHub poll while
    CI runs; real time is not needed. Running checks are visible instead: rows
    with running checks show a running mark, and the header shows how many
    builds are running, so I know when a manual refresh is worth it.
18. Actions run id: GraphQL (`checkSuite { workflowRun { databaseId } }`),
    fetched only when an action or the detail view needs it. Chosen over URL
    parsing because it does not break when GitHub changes its URLs, and the
    lazy fetch keeps the cost off the main query.
19. Jenkins trust rules come from config: exact host list and the job URL
    pattern that allows Build Now. (Queue following is fixed behavior since
    item 27.)
20. Confirmations use a k9s-style modal: a dialog that names the action and the
    exact target, with Cancel selected by default and OK one key away.

21. Multiple ticket keys: one primary key, no picker. Keys from the title win,
    then the branch name; the PR body is used only when neither has a key. `t`
    and `m` act on the primary key; other keys show in the detail view.
    Revisit if it picks the wrong ticket.
22. Config: TOML at `~/.config/ghtop/config.toml`, overridable with
    `--config` (lookup chain and `version` field dropped in item 27). TOML
    chosen after comparing examples (`config.md`): no indentation rules, no
    type surprises, raw single-quoted strings for regex. The new file name
    also cannot collide with the old attempt's `config.yaml`. PR titles are
    shown as written; stripping a leading ticket key is an opt-in setting. Key
    patterns use Go regex syntax (RE2), matched case-insensitively; keys are
    stored in upper case.
23. Glyphs: single-width symbols only (`✓ ✗ ● ○ ! –`), no emoji and no emoji
    option. Mockups at 120 columns, plus one 80-column mockup showing which
    columns drop first.
24. Deferred topics are kept in `DEFERRED.md` and curated by the author.

25. Added during drafting (accepted by author 2026-11-08; amended by item
    27): GitHub access through a `gh` subprocess with a closed command list
    (section "GitHub access" below); one shared process runner for `gh` and
    `twg`; `BurntSushi/toml`; MIT license; pre-commit leak
    guard reading a private denylist; PR template; Jenkins state from
    `<job>/lastBuild/` so Jira and Jenkins refresh while GitHub data is
    stale.
26. Tool versions: tested with `gh` 2.103.3 and `twg` 1.3.8 (installed on the
    author's machine on 2026-11-08); no version check at run time (item 27).
    Go: latest stable at the start of coding.

27. Plan review, 2026-11-09 (Goldfish Stage 9 plus an over-engineering pass;
    log in [docs/reviews/2026-11-09-decisions.md](../reviews/2026-11-09-decisions.md)). ghtop is a personal tool: one user, macOS
    and Linux, no CI.
    *   Planning: one spec kept (`services/github.md`, the explicit command
        list); other specs, the per-file review gate, glossary, layout file
        and mockups dropped. ADR files dropped; 0009 folded into this file.
        Old docs deleted, not archived.
    *   Milestones: M1 read-only GitHub with a framework check (replaces the
        separate spike, item 11), M2 Jira and Jenkins state, M3 detail and
        actions.
    *   Tooling: no CI, no coverage targets, no Makefile. `pre-commit` runs
        gofmt, go vet, golangci-lint (v2 config, defaults plus gosec), `go
        test` on push, and the leak guard. `--version` from build info.
    *   Runtime: config path `~/.config/ghtop/config.toml` or `--config`, no
        `version` key, no `${VAR}`; no `ghtop doctor`, no minimum-version
        checks; three error hints (auth expired, VPN off?, rate limited);
        debug log never records headers or bodies; header shows remaining
        GitHub budget, no floor or hourly cap; concrete clients, `proc.Runner`
        the only interface; Jenkins Build Now with default parameters, job
        picker, queue checked at 10 s and 20 s, no crumb, no presets.
    *   Decided open questions: Merged view uses `updated:>=`; org required;
        leak guard is a pre-commit hook with a private denylist file; latest
        major library versions; "ready to merge" from GitHub's
        `reviewDecision` and `mergeStateStatus`.
    *   Round 2 (re-audit): copy PR/ticket URL (`c`/`C`) dropped, so no
        clipboard code; see `DEFERRED.md`.
    *   Round 2 (re-audit): "behind" shown from M1 through one REST compare
        per open PR (`gh api repos/<owner>/<repo>/compare/<base>...<head>`,
        `behind_by`), for the active view only, never Merged; conflicts still
        from `mergeStateStatus`.

Open, to settle in the planning files (see `CHECKLIST.md` for where):

- Fast Jenkins poll (later phase): trigger, interval, maximum duration.

## GitHub access

Folded in from decision record 0009 (accepted 2026-11-08), amended by item 27.

### Context

ghtop needs GitHub for: one GraphQL search per view, a count-only query for
Review-requested, one REST compare per open PR for behind-by, REST calls for Actions runs and jobs,
re-run of failed jobs, and update-branch. The `gh` CLI is a prerequisite and
already holds the login. pr-tracker calls `gh api graphql` as a subprocess.

### Facts checked (2026-11-08)

*   **Rate limits are the same for every option.** All three use the same token
    from `gh`, so they draw on the same budgets: 5000 GraphQL points per hour
    and 5000 REST requests per hour, plus GitHub's secondary limits. `gh api`
    makes no hidden extra calls. GraphQL returns `rateLimit { cost remaining
    resetAt }` in the body either way; for REST, the remaining count is in
    response headers, which the library exposes directly and the subprocess
    shows only with `gh api -i`.
*   **gh-dash uses both**: reads go through `go-gh`
    (`gh.DefaultGraphQLClient()` in `internal/data/prapi.go`, with
    `shurcooL-graphql` for typed queries); actions run the `gh` CLI as a
    subprocess (`exec.Command("gh", ...)` in
    `internal/tui/components/tasks/pr.go`).

### Options

*   **A: run the `gh` CLI as a subprocess** (`gh api graphql`, `gh api` for
    REST, `gh pr update-branch`). Uses whatever host and auth `gh` has, no
    token handling in ghtop, easy to test with a fake runner; each call costs
    a process start (tens of ms); errors arrive as exit codes and stderr text.
    Fails when `gh` output or error text changes between versions.
*   **B: the `go-gh` library**, reading token and host from `gh`'s config and
    making HTTP calls in ghtop. Typed errors, no process starts, installable
    as `gh ghtop`; ghtop holds the token and must keep it out of logs. Fails
    when `gh` stores the token where `go-gh` cannot read it, or the library's
    API changes.
*   **C: library for reads, `gh` subprocess for writes** (gh-dash's pattern).
    Two access paths to test and two error formats to map; fails when the two
    paths disagree on host or auth.

### Decision

Option A: ghtop calls the `gh` CLI as a subprocess.

*   **Two layers.**
    *   Concrete clients used by the rest of ghtop: `github.Client` (search
        per view, review-requested count, behind-by, update branch) and
        `actions.Client` (runs, jobs, re-run failed), with domain-level
        methods. Callers never see `gh` arguments or output, so a later switch
        to option B or C rewrites these packages only. No interfaces until a
        second implementation exists (item 27).
    *   Below them, a small runner (`proc.Runner`) is the only code that
        starts processes: `Run(ctx, name, args) -> stdout, stderr, exit code`
        for `gh` and `twg`, and `Start(name, args) -> error` for the browser
        opener, which runs detached (output to `/dev/null`, `cmd.WaitDelay`
        set, only a failure to start is reported).
*   **A closed command list.** Every `gh` and `twg` command ghtop runs is
    listed, with placeholders, in `services/github.md`, so each can be run by
    hand to check access and output shape. No command is built outside this
    list.

Rejected by author for now: option B (more code, token handling in ghtop) and
option C (two access paths).

### Consequences

*   **Domain-level methods.** No `RunGh(args)` exposed to callers.
*   **Arguments as a list, never through a shell.** GraphQL values go in as
    variables, never pasted into the query text (pr-tracker pastes names into
    its behind-by query; ghtop does not). Queries are embedded in the binary
    and passed inline as `-f query=<text>`. Repo names, branch names and
    numbers are validated first.
*   **`-f` for strings.** `-f` (raw string) for every string value; `-F` only
    for numbers and booleans that ghtop itself produces. Why: `-F` reads a
    file when the value starts with `@`, converts true/false/null/numbers, and
    fills `{owner}`/`{repo}`/`{branch}`; branch names and titles from other
    people's PRs are untrusted.
*   **No prompts, no pager, no color.** Run with `GH_PROMPT_DISABLED=1`,
    `GH_PAGER=` (empty), `NO_COLOR=1`, so a `gh` command can never wait for
    input or open a pager behind the terminal UI.
*   **Timeouts and cancel.** Every call has a 30 s timeout and is killed on
    quit. Leaving a view does not cancel its fetch; the result fills that
    view's cache.
*   **Error mapping.** Exit code plus stderr map to three hints: `(HTTP
    401)`/"gh auth login" -> auth expired; rate-limit text -> rate limited.
    Anything else shows the last stderr line. Tests pin these strings, so a
    `gh` upgrade that changes them fails a test instead of the UI.
*   **Partial GraphQL errors.** `gh api graphql` exits non-zero when the
    response has `errors`, even when `data` is present (for example one repo
    behind SAML/SSO, one node timeout). With `data`, ghtop shows the rows and
    the `errors` messages as a status-bar warning (source stays ok); the fetch
    fails (source stale, hint mapping) only when there is no `data`.
*   **Budget reading.** GraphQL queries request `rateLimit { cost remaining
    resetAt }`; the header shows the remaining budget.
*   **Concurrency cap.** At most 4 processes at once (constant), so opening the
    Actions view on a PR with many runs does not start dozens of processes.
    The detached browser opener does not count against it.
*   **Tests** use a fake runner that returns recorded, scrubbed outputs
    (placeholders only); no test starts a real `gh`.
*   **Logs** with `--debug` record the command name, arguments (query file
    name instead of query text), duration and exit code; `gh` never prints the
    token.
