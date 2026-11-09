# 0009: How ghtop calls GitHub

*   **Status:** Accepted
*   **Date:** 2026-11-08
*   **Architecture:** [architecture.md](../architecture.md), section
    "GitHub access"

## Context

ghtop needs GitHub for: one GraphQL search per view, a count-only query for
Review-requested, a behind-by query, REST calls for Actions runs and jobs,
re-run of failed jobs, and update-branch. The `gh` CLI is a prerequisite and
already holds the login. pr-tracker calls `gh api graphql` as a subprocess.

## Facts checked (2026-11-08)

*   **Rate limits are the same for every option.** All three use the same token
    from `gh`, so they draw on the same budgets: 5000 GraphQL points per hour
    and 5000 REST requests per hour, plus GitHub's secondary limits. `gh api`
    makes no hidden extra calls. Reading the budget differs: GraphQL returns
    `rateLimit { cost remaining resetAt }` in the body either way; for REST,
    the remaining count is in response headers, which the library exposes
    directly and the subprocess shows only with `gh api -i`.
*   **gh-dash uses both** (checked in its source): reads go through `go-gh`
    (`gh.DefaultGraphQLClient()` in `internal/data/prapi.go` and siblings,
    with `shurcooL-graphql` for typed queries); actions run the `gh` CLI as a
    subprocess (`exec.Command("gh", ...)` in
    `internal/tui/components/tasks/pr.go`, for example `gh pr ...` and
    `gh api -X POST ...`).

## Options


*   **Option A: run the `gh` CLI as a subprocess** (`gh api graphql`, `gh api`
    for REST, `gh pr update-branch`).
    *   Mechanism: same as pr-tracker; every call starts a `gh` process and
        parses its JSON output.
    *   Trade-offs: uses whatever host and auth `gh` has, with no token
        handling in ghtop; easy to test by swapping in a fake `gh`; each call
        costs a process start (tens of ms); errors arrive as exit codes and
        stderr text that ghtop must parse.
    *   Fails when: the `gh` output or error text changes between versions, or
        many small calls (per-run job lists) make process starts add up.
*   **Option B: use the `go-gh` library** (GitHub's Go package for `gh`
    extensions), which reads the token and host from `gh`'s config and makes
    HTTP calls inside ghtop.
    *   Mechanism: one in-process HTTP client for GraphQL and REST.
    *   Trade-offs: typed errors and HTTP status codes (rate limits, 502/504
        are clear); no process start per call; ghtop can also be installed as
        `gh ghtop`; ghtop now holds the token in memory and must keep it out
        of logs; tests need a fake HTTP server.
    *   Fails when: `gh` stores the token in a way `go-gh` cannot read (for
        example a new credential store), or the library's API changes on
        upgrade.
*   **Option C: library for reads, `gh` subprocess for actions** (gh-dash's
    pattern).
    *   Mechanism: searches, counts and run/job lists through `go-gh`;
        re-run, update-branch and other writes through `gh` commands.
    *   Trade-offs: polling gets typed errors and no process starts; writes
        reuse `gh`'s own command behavior and messages, and are rare enough
        that process start cost does not matter; two access paths to test and
        two error formats to map.
    *   Fails when: the two paths disagree (for example a host or auth setting
        honored by `gh` but not by `go-gh`), so a read works and a write fails,
        or the reverse.

## Decision

Option A: ghtop calls the `gh` CLI as a subprocess, behind its own interfaces,
so the implementation can be swapped later (for example for `go-gh`, option B
or C) without changing callers.

*   **Two layers.**
    *   Domain interfaces used by the rest of ghtop: `PRSource` (search per
        view, review-requested count, behind-by, update branch) and
        `ActionsProvider` (runs, jobs, re-run failed). Callers never see `gh`
        arguments or output.
    *   One implementation package that turns each method into one known `gh`
        command and parses its JSON. Below it, a small runner
        (`Run(ctx, args) -> stdout, stderr, exit code`) is the only code that
        starts processes.
*   **A closed command list.** Every `gh` command ghtop runs is listed, with
    placeholders, in `services/github.md`. The list is also a manual smoke
    test: each command can be run by hand to check access and output shape.
    No command is built outside this list.

Rejected by author for now: option B (more code, token handling in ghtop) and
option C (two access paths). Either stays possible behind the same interfaces.

## Consequences

Rules the subprocess implementation must follow (details in
`services/github.md`):

*   **Interfaces stay domain-level.** No `RunGh(args)` in the interface; that
    would make a later swap rewrite every caller.
*   **Arguments as a list, never through a shell.** GraphQL values go in as
    variables (`-f`/`-F`), never pasted into the query text. (pr-tracker builds
    its behind-by query by pasting names into the text; ghtop does not.)
    Repo names, branch names and numbers are validated first.
*   **No prompts, no pager, no color.** Run with `GH_PROMPT_DISABLED=1`,
    `GH_PAGER=` (empty), `NO_COLOR=1`, so a `gh` command can never wait for
    input or open a pager behind the terminal UI.
*   **Timeouts and cancel.** Every call has a timeout and is killed on quit or
    when its view is left (Go's context-aware process start; macOS has no
    `timeout` command).
*   **Error mapping.** Exit code plus stderr are mapped to ghtop's error
    classes: `(HTTP 401)`/"gh auth login" -> auth expired; rate-limit text or
    `(HTTP 403)` with rate-limit wording -> rate limited; `(HTTP 502)`/`(HTTP
    504)` -> upstream timeout; `gh` not found -> tool missing. Unknown text ->
    a generic error that shows the last stderr line. Tests pin these strings,
    so a `gh` upgrade that changes them fails a test instead of the UI.
*   **Budget reading.** GraphQL queries request `rateLimit { cost remaining
    resetAt }`. REST calls that matter for the budget use `gh api -i` and read
    the `x-ratelimit-*` headers.
*   **Concurrency cap.** At most a few `gh` processes at once (configurable),
    so opening the Actions view on a PR with many runs does not start dozens
    of processes.
*   **Minimum `gh` version.** Checked at start and by `ghtop doctor`
    (`gh --version`), since `gh pr update-branch` and some JSON fields exist
    only in newer versions.
*   **Tests** use a fake runner that returns recorded, scrubbed outputs
    (placeholders only); no test starts a real `gh`.
*   **Logs** with `--debug` record the command name, arguments without bodies,
    duration, exit code and the GraphQL cost; `gh` never prints the token.
