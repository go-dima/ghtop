# ghtop: external commands

*   **Status:** Draft, 2026-11-09. A working list, not a full spec: each entry is
    filled in (exact flags, sample output, fields read) when the milestone that
    needs it starts. Commands marked *unverified* have not been run yet.
*   **Rules:** [concepts_brief.md, "GitHub access"](../concepts_brief.md#github-access).
    `-f` for every string value; `-F` only for numbers and booleans ghtop
    produces. Queries are embedded files passed as `-f query=<text>`. All
    calls go through `proc.Runner.Run` (4 at once, 30 s timeout).
*   **Placeholders:** `example-org`, `<owner>/<repo>`, `<n>` (PR number),
    `<sha>`, `<date>` (`YYYY-MM-DD`), `EX-123`.

Every `gh` and `twg` command ghtop runs is listed here, and no other
command is added in code without adding it here first (file 19 mirrors this
list). Jenkins is plain HTTP, not a command: see implementation.md files 25
and 26.

## GitHub (`gh`)

| # | Name | Milestone | Command | Reads |
|---|---|---|---|---|
| G1 | auth check | M1 | `gh auth status` | exit code (0 = logged in) |
| G2 | search: Open | M1 | `gh api graphql -f query=<open.graphql> -f q='is:pr is:open author:@me org:example-org archived:false'` | rows, `issueCount`, `rateLimit` |
| G3 | search: Merged | M1 | `gh api graphql -f query=<closed.graphql> -f q='is:pr is:closed author:@me org:example-org updated:>=<date>'` | rows incl. `state`, `merged`, `mergedAt`, `closedAt` |
| G4 | search: Review-requested | M1 | `gh api graphql -f query=<open.graphql> -f q='is:pr is:open review-requested:@me org:example-org archived:false'` | rows |
| G5 | search: Involved | M1 | `gh api graphql -f query=<open.graphql> -f q='is:pr is:open involves:@me -author:@me org:example-org updated:>=<date>'` | rows |
| G6 | review-requested count | M1 | `gh api graphql -f query=<count.graphql> -f q=<G4 query>` | `issueCount`, `rateLimit` |
| G7 | behind-by | M1 | `gh api repos/<owner>/<repo>/compare/<base>...<head>` (plain GET; segments path-escaped by ghtop) | `behind_by` |
| G8 | update branch | M3 | `gh api -X PUT repos/<owner>/<repo>/pulls/<n>/update-branch -f expected_head_sha=<sha>` *unverified* | 202 + message; 422 on conflict/moved head |
| G9 | Actions run id | M3 | `gh api graphql -f query=<run_id.graphql> -f owner=<owner> -f repo=<repo> -F number=<n>` | check suites (`app.slug`, `conclusion`, `workflowRun.databaseId`); cost 1 |
| G10 | run jobs | M3 | `gh api repos/<owner>/<repo>/actions/runs/<run>/jobs` *unverified* | jobs, steps, conclusions |
| G11 | re-run failed | M3 | `gh api -X POST repos/<owner>/<repo>/actions/runs/<run>/rerun-failed-jobs` *unverified* | 201 |

Notes:

*   `<date>` is today minus `github.closed_days` (G3) or
    `github.involved_days` (G5).
*   `org:` comes from `github.org` (required). `@me` is resolved by GitHub.
*   G2-G5 return at most the PR cap per view; when `issueCount` is larger the
    UI shows the "truncated" warning.
*   `mergeStateStatus` needs no preview header: G2 returned `BEHIND`,
    `BLOCKED` and `CLEAN` without it.
*   G7 uses the REST core quota (5000/hour), separate from the GraphQL points
    shown in the header.

### Verified 2026-11-09 (`gh` 2.45.0, real org)

*   **G2:** works with `-F first=50`; 9 PRs cost 27 points with the caps
    below. `statusCheckRollup` is `null` for a PR with no checks (R9: counts
    as "CI ok"). Jenkins results arrive as `CheckRun`s from a GitHub App (its
    own app slug), not as `StatusContext`s; `jenkins.Match` still works on
    `detailsUrl`.
*   **G6:** works with `first: 0` (cost 1).
*   **G9:** works (cost 1). G2 already returns
    `checkSuite.workflowRun.databaseId` for every Actions check run, so G9 may
    not be needed (decide at M3).

## Jira (`twg`)

All with `-o json`. Site and user come from `twg`'s own login profile.

| # | Name | Milestone | Command | Reads |
|---|---|---|---|---|
| T1 | auth check | M2 | `twg whoami -o json` | exit code, account |
| T2 | fetch tickets | M2 | `twg jira workitem bulk-get EX-123 EX-456 -o json` *unverified* (one call for all keys in the view) | key, status, summary |
| T3 | transitions | M3 | `twg jira workitem transitions ... EX-123 -o json` *unverified: subcommand shape* | transition ids and target statuses |
| T4 | move ticket | M3 | `twg jira workitem transition --id EX-123 ...` *unverified: flags* | new status |

Keys are validated against `tracker.key_pattern` before any call. Auth
failure hint: `twg login --force`.

## Browser opener (not `gh`/`twg`)

`open <url>` (macOS) / `xdg-open <url>` (Linux) through `proc.Runner.Start`
(detached). URLs are built by ghtop: PR URL from GitHub, ticket URL from
`tracker.site`, Jenkins build URL from the trusted job URL.

## Caps (initial values; tune after the first real run)

Read the `rateLimit.cost` of each search in the `--debug` log, then adjust.

| Cap | Value |
|---|---|
| PRs per view (search `first:`) | 50 |
| checks per PR (rollup contexts) | 100 |
| review threads per PR | 50 |
| reviews per PR | 50 |
| conversation comments per PR (`last:`) | 50 |
