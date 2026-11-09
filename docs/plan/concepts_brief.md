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
re-run a failed Actions run, start a Jenkins "Build Now" (with parameters when
needed), and see why a run failed.

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
A plan with 10+ files repeats that pattern at a larger size. The plan must name
the root cause of the old UI bugs. Candidates seen in the old plans: the
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
only on job URLs that match a configured pattern.

### 4. Public repo: organization data leaks easily

pr-tracker has organization values in more places than its config file: the
title-cleanup regex, the key regex in the server, the Jenkins job naming rule
(`<repo>_<arch>`), the "ready to merge" rule (two approvals), the status names in
the sort order, the env file in `package.json`, and the guide text. Copying ideas
from it brings these values along. Rules for ghtop:

- Specs, mockups and test data use placeholders only (`example-org`, `EX-123`,
  `ci.example.com`).
- A local pre-commit check greps for the private values. The list comes from the
  private config, so it is not in the repo.
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
  with no Jenkins check yet has no job URL to use unless the config has a URL
  template. API-token auth is normally exempt from the CSRF crumb; on "No valid
  crumb", fetch one and retry once. One in-flight trigger per job.

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
    if several), `a` Actions run view, `c`/`C` copy PR/ticket URL, `r`
    refresh, `?` help, `:` command, `/` filter, `Enter` detail. Every change
    goes through the `Ctrl-A` action menu, then confirm: `r` re-run failed
    jobs, `b` Jenkins Build Now, `u` update branch, `m` Jira quick move.
  * Actions run view (`a`): the PR's workflow runs, their jobs and state, and
    the failed steps, fetched on open; open in browser as a second step.
  * Update branch: merge the base branch into the PR branch when it is behind
    and has no conflicts; with conflicts, open the PR page; no action while
    GitHub has not computed the state. Merge only (rebase deferred).
  * Refresh every 5 minutes plus manual, active view only; Review-requested
    count in the background.
  * Source health strip and stale-data marking.
  * Private config with a version field; placeholder-only public repo.
* **In-Scope, later phases:**
  * Fast Jenkins poll while builds run.
  * Jenkins Build Now with parameters (v1: no-parameter Build Now and config
    presets).
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
    right away and refreshes in the background.
14. Planning set: the full file tree in `CHECKLIST.md`. Each file is drafted or
    edited by a small, single-purpose agent that gets the brief, the checklist
    rules and the files it depends on; the author reviews each file.
15. Process: every decision is recorded in `docs/decisions/` (one file per
    decision), and `docs/architecture.md` keeps Mermaid diagrams of the system,
    updated in the same change as the code.

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
19. Jenkins trust rules come from config: exact host list, the job URL pattern
    that allows Build Now, and whether to follow the queue item to the new
    build.
20. Confirmations use a k9s-style modal: a dialog that names the action and the
    exact target, with Cancel selected by default and OK one key away.

21. Multiple ticket keys: one primary key, no picker. Keys from the title win,
    then the branch name; the PR body is used only when neither has a key. `t`
    and `m` act on the primary key; other keys show in the detail view.
    Revisit if it picks the wrong ticket.
22. Config: TOML at `~/.config/ghtop/config.toml` (honours `$XDG_CONFIG_HOME`),
    overridable with `GHTOP_CONFIG` or `--config`; a `version` field. TOML
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

25. Added during drafting (accepted by author 2026-11-08): GitHub access
    through a `gh` subprocess behind domain interfaces (`PRSource`,
    `ActionsProvider`, Jenkins client, `Tracker`) with a closed command list
    (decision 0009); one shared process runner for `gh` and `twg`;
    `BurntSushi/toml`; OSC 52 clipboard; MIT license; pre-commit leak guard
    reading a private denylist; GitHub CI workflow; PR template; Jenkins state
    from `<job>/lastBuild/` so Jira and Jenkins refresh while GitHub data is
    stale.
26. Tool versions: minimum `gh` 2.103.3 and `twg` 1.3.8 (installed on the
    author's machine on 2026-11-08; `gh` 2.103.3 is the latest release). Go:
    latest stable at the start of coding (not installed yet).

Open, to settle in the planning files (see `CHECKLIST.md` for where):

- Root cause of the old UI bugs.
- Merged view filter: `merged:>=` or `updated:>=` (pr-tracker uses `updated`,
  which includes closed-unmerged PRs).
- GitHub budget: the query split is an implementation detail for
  `core/refresh.md` and `services/github.md`. The brief keeps only the
  constraint: refresh stays at or under 1500 points per hour by default,
  measured from the cost GitHub returns.
- Fast Jenkins poll (later phase): trigger, interval, maximum duration.
- Leak-guard mechanism.
