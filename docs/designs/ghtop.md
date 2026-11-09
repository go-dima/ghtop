# ghtop

*   **Author:** Dima Gonikman
*   **Status:** Proposed
*   **Date:** 2026-11-08

This document is the entry point for ghtop's design: problem, goals, scope and
user journeys. Everything else lives in small linked files, each fact in one
file only: the technical plan in [architecture.md](../architecture.md),
decisions in `docs/decisions/`, detailed specs in `docs/plan/` (`core/`,
`views/`, `services/`, `config.md`). Files link to each other and never copy.
Predecessor: [concepts_brief.md](../plan/concepts_brief.md). Planning files
and progress: [CHECKLIST.md](../plan/CHECKLIST.md).

--------------------------------------------------------------------------------

## Overview

ghtop is a terminal app for following my pull requests and everything attached
to them: reviews, CI runs (GitHub Actions and Jenkins) and the issue-tracker
ticket (Jira). It works like k9s: one full-screen table, keyboard navigation,
and single-key actions on the highlighted row.

It has four views of the same PR table, one on screen at a time:

| View | What it shows | GitHub search |
|---|---|---|
| Open | my open PRs | `is:pr author:@me org:<org> is:open` |
| Merged | my PRs closed in the last 14 days | `is:pr author:@me org:<org> is:closed` + date filter |
| Review-requested | PRs where my review is requested now | `is:pr review-requested:@me org:<org> is:open` |
| Involved | open PRs by others that involve me, active in the last 14 days | `is:pr involves:@me -author:@me org:<org> is:open updated:>=<date>` |

Every row shows the PR, its state, its reviews, a CI summary and its ticket.
From a row I can open the PR, the ticket or a build in the browser, move the
ticket to another status, re-run a failed Actions run, or start a Jenkins
build.

ghtop depends on the `gh` CLI for GitHub access. Jira (through the `twg` CLI)
and Jenkins (through its REST API and `JENKINS_TOKEN`) are optional: when one is
not reachable, ghtop still shows links to it but pulls no data.

The repository is public. All organization data (org name, Jira site, key
pattern, Jenkins host, transition names) lives in a private config file on my
machine.

## The Problem

My daily PR work is spread over four places: GitHub for the PR and Actions,
Jenkins for the builds the company runs on every PR, Jira for the ticket, and
the terminal where I work. To answer "what needs my attention now?" and to act
on it (re-run a failed run, start a build, update a branch, move a ticket), I
switch between several browser tabs.

The proposed solution is a terminal tool, written in Go with Bubble Tea, that
puts my PRs, their CI and their tickets in one table and runs those actions
from the keyboard.

The first ghtop attempt (Python + Textual) did not get there: it browsed
org -> repo -> PR -> actions, made one `gh run list` call per PR, and its UI was
broken (focus, freezes). This design replaces it.

Related tools used as references, not as problems to fix:

*   **pr-tracker** (my local web page): the source of the data ideas, including
    the GitHub query, Jira key extraction, Jenkins state from PR checks, and the
    known limits (GitHub's 10 s query limit, VPN detection, `twg` login expiry).
    It keeps running; ghtop shares ideas with it, not code.
*   **gh-dash**: the source of the interaction ideas (keyboard shortcuts, PR
    detail view) and of the stack.

## Goals

*   **One screen answers "what needs me?"** The Open view shows every open PR I
    authored in the configured org with: PR state (draft, conflicts, behind
    base), approvals and requested changes, unanswered review threads, a CI
    summary covering both Actions and Jenkins, and the primary ticket key with
    its status.
*   **Four views, one table.** Open, Merged (14 days), Review-requested and
    Involved (open, 14 days) are separate views on the same table component.
    A view differs only in its data source.
*   **Act without leaving the terminal**, each action on the highlighted row
    and confirmed in a dialog that names the target:
    *   `o` open the PR in the browser
    *   `t` open the ticket in the browser
    *   `b` open a Jenkins build in the browser (picker when the PR has
        several Jenkins jobs)
    *   `a` open the Actions run drill-down: the PR's workflow runs, their jobs
        and state, and the failed steps, shown in ghtop (fetched from GitHub's
        REST API only when opened). Opening the run in the browser is a
        second step from there. Also reachable from the PR detail view.
    *   `Ctrl-A` opens the action menu for the row: every action that changes
        something (on GitHub, Jenkins or Jira) is a letter in this menu, and
        the menu lists only the actions that apply to this PR right now
        (keys: [core/keymap.md](../plan/core/keymap.md)). The actions:
    *   move the ticket by a configured quick move
    *   re-run a failed GitHub Actions run
    *   Jenkins Build Now on the PR job, with configured parameter presets
    *   **update branch** when the PR is behind its base branch (the base the PR
        targets, for example `develop` or `main`): if GitHub reports no
        conflicts, ghtop merges the base into the PR branch through GitHub's
        update-branch API (`gh pr update-branch`); if there are conflicts, the
        same key opens the PR page in the browser instead. Uses merge, not
        rebase (rebase deferred). When GitHub has not yet computed whether the
        PR is behind or conflicting, the key does nothing and the status bar
        says so. The update starts a new round of CI on the PR, and the local
        checkout must be pulled afterwards; the confirm dialog says both.
*   **Navigation like k9s:** arrow keys and `j/k`, `Enter` for the PR detail
    view, `Esc` back, `/` filter, `:` commands, `?` help, `r` refresh.
*   **Stay inside the GitHub budget.** Refresh uses at most 1500 GraphQL points
    per hour by default, measured from the cost GitHub returns. Only the view
    on screen is fetched; Review-requested also runs a count-only query in the
    background to show a count in the header.
*   **Refresh rules:** every 5 minutes and on `r`; no faster poll while CI
    runs. Rows with running checks show a running mark and the header shows how
    many builds are running, so I can see when a manual refresh is worth it.
    Switching views shows cached rows with their age at once, then refreshes.
*   **Each source refreshes on its own.** Jira and Jenkins do not wait for a
    good GitHub fetch: when GitHub fails, ghtop keeps the last PR rows and
    still refreshes ticket status (by the keys it already has) and build state
    (by the Jenkins jobs it already has, asking each job for its last build so
    a new build number is picked up). What a stale GitHub fetch cannot show:
    new PRs, new commits, and builds of a Jenkins job not seen before. The
    header shows each source's age; cells from a stale source get a stale
    mark.
*   **Partial failure never blanks the screen.** When GitHub, Jira or Jenkins
    fails, ghtop keeps the last rows, marks them stale, and shows a per-source
    status with a fix hint (for example "VPN off?" for a Jenkins 403 without an
    `x-jenkins` header, or `twg login --force` for an expired Jira login).
*   **Optional sources.** On start and on manual refresh, ghtop checks whether
    Jira and Jenkins are reachable and sets a flag per source. Without access,
    rows still link to the ticket and build.
*   **Nothing private in the repo.** Config is TOML at
    `~/.config/ghtop/config.toml` (overridable). The repo, docs, mockups and test
    data use placeholders only (`example-org`, `EX-123`, `ci.example.com`).
*   **Safe CI triggers.** `JENKINS_TOKEN` is sent only to an exact host from
    config, and Build Now runs only on job URLs that match a configured pattern.

## Non-Goals

*   **Org -> repo -> PR browsing**, and any per-PR `gh run list` polling. ghtop
    is user-centric: one search per view.
*   **A general Jenkins job browser.** ghtop only knows the builds linked to
    PRs through their checks.
*   **An in-app log viewer** in the first version. Failure reason = failed check
    names and summaries, then the full log in the browser or `$PAGER`.
*   **A plugin system** for trackers or CI. Small internal interfaces with one
    implementation each.
*   **Changed-row highlighting and acknowledge** (pr-tracker feature).
*   **Emoji glyphs.** Single-width symbols only.
*   **Multiple orgs, Windows, user-overridable keymap, disk cache.** Tracked in
    [DEFERRED.md](../plan/DEFERRED.md).
*   **Sharing code with pr-tracker** or depending on its server.

## Open Questions

*   **Root cause of the old UI bugs**: framework focus handling, the per-PR
    polling, or refresh results arriving while the cursor moved. Author to
    write down from memory (see [TASKS.md](../plan/TASKS.md)).
*   **Merged view filter**: `merged:>=` (merged only) or `updated:>=` (also
    closed-unmerged, as pr-tracker does).
*   **Org filter when config has no org**: search all of GitHub for
    `author:@me`, or refuse to start.
*   **Leak-guard mechanism**: a local pre-commit grep built from the private
    config.

## Critical User Journeys (CUJs)

### CUJ 1: Morning check of my open PRs

*   **Given**: `gh` is logged in, the config names the org, Jira and Jenkins
    are reachable.
*   **When**: I run `ghtop`.
*   **Then**: the Open view shows my open PRs within one GitHub query, with
    reviews, CI summary and ticket status filled in as Jira and Jenkins answer.
    PRs with failed CI sort first. The header shows each source as `ok` with
    its age, and the Review-requested count.

### CUJ 2: Re-run a failed Actions run

*   **Given**: a row shows a failed Actions run.
*   **When**: I press `a`, move to the failed run, and press `Ctrl-A` `r`.
*   **Then**: a dialog names the repo, PR, workflow and run; on OK, ghtop asks
    GitHub to re-run the failed jobs, shows the result in the status bar, and
    the row shows a running mark after the next refresh.

### CUJ 3: Start a Jenkins build

*   **Given**: a PR whose check points to a Jenkins job that matches the
    configured job pattern on an allowed host.
*   **When**: I choose Build Now (from the PR detail view or the `b` picker),
    optionally with a configured parameter preset.
*   **Then**: a dialog names the job; on OK, ghtop posts the build request,
    follows the queue item to the new build number, and shows it in the status
    bar with a link.

### CUJ 4: Update a branch that is behind

*   **Given**: a row shows "behind" and GitHub reports no conflicts.
*   **When**: I press `Ctrl-A` and choose update branch.
*   **Then**: a dialog says the base branch will be merged in, CI will run
    again and the local checkout needs a pull; on OK, GitHub updates the branch.
    With conflicts, the same key opens the PR page instead. When GitHub has not
    computed the state yet, nothing happens and the status bar says why.

### CUJ 5: Move the ticket after merge

*   **Given**: the Merged view shows a PR whose ticket is in Code Review.
*   **When**: I press `Ctrl-A` and choose move ticket.
*   **Then**: ghtop finds the one configured quick move for that status, asks
    for confirmation naming the ticket and target status, runs it through
    `twg`, and refreshes the ticket status. If zero or several transitions
    match, nothing changes and the status bar says to do it in Jira.

### CUJ 6: VPN is off

*   **Given**: the Jenkins host answers 403 without an `x-jenkins` header.
*   **When**: a refresh runs.
*   **Then**: GitHub and Jira data refresh as usual; Jenkins cells keep their
    last values with a stale mark; the header shows `Jenkins: VPN off?`. No
    error dialog interrupts navigation.

## Technical Plan (Architecture)

The technical plan and the diagrams live in
[docs/architecture.md](../architecture.md): stack, system context, components,
data model summary, data flow of one refresh, GitHub, Jira and Jenkins access,
errors and source health, config, and the open GitHub access decision
([0009](../decisions/0009-github-access.md)).

## Alternatives Considered

Fifteen paths not taken, each with pros, cons and the reason for rejection, are
in [alternatives.md](../plan/alternatives.md): product shape (gh-dash config, fork,
pr-tracker client, pr-tracker terminal mode, repo-first navigation, Python +
Textual), views, refresh, and technical choices (GitHub access, config format,
plugin system, one large document).

## Detailed Implementation Plan

Every file to create, change or move, the milestones (M0 spike to M7
operability), libraries and the verification plan are in
[implementation.md](../plan/implementation.md).

--------------------------------------------------------------------------------

*Drafted with EGM*
