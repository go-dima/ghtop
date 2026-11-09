# ghtop: alternatives considered

*   **Status:** Draft
*   **Design doc:** [ghtop.md](../designs/ghtop.md)

Each alternative was weighed during the brainstorm or drafting and rejected.
Deferred ideas that may come back are in [DEFERRED.md](./DEFERRED.md); this
file holds the paths not taken for the main design.

## Product shape

### A. gh-dash with a private config and shell scripts

*   **Pros**: no new tool; gh-dash already has PR sections from search
    filters, a PR detail view, and custom keys that run shell commands with the
    repo, PR number and branch. Nothing private in any public repo.
*   **Cons**: no Jira status or live Jenkins state in the table; no overview of
    tickets and builds per PR; actions would be shell one-liners with no
    confirm dialog naming the target.
*   **Reason for rejection**: Rejected by author after a trial: gh-dash covers
    the PR data and its PR view fits the drill-down role, but the main need is
    an overview with Jira, Jenkins and CI actions, which it lacks.

### B. Fork gh-dash

*   **Pros**: working PR detail view, keymap, help and resize/focus handling on
    day one.
*   **Cons**: the parts ghtop changes most (row model, fetch code, overview,
    actions, Jira and Jenkins data) are the core of gh-dash, so every upstream
    update becomes a manual merge; a fork that drifts ends as a rewrite inside
    someone else's structure.
*   **Reason for rejection**: Rejected by author: a new tool on the same stack
    (Go + Bubble Tea) keeps gh-dash as a reference without the merge cost.

### C. Terminal client over pr-tracker's HTTP API

*   **Pros**: least code; reuses pr-tracker's data handling (caps, the light
    closed-PR query, VPN detection, Jira moves).
*   **Cons**: needs the pr-tracker server running; ghtop's data model and
    refresh rules would be limited to what pr-tracker returns; ties two tools
    together.
*   **Reason for rejection**: Rejected by author: ghtop is a separate tool that
    shares ideas with pr-tracker, not code or a server.

### D. A terminal mode inside pr-tracker

*   **Pros**: one codebase, one data layer.
*   **Cons**: pr-tracker uses Node with no packages and no build step, which
    makes a terminal UI hard to build; mixes two interfaces in one tool.
*   **Reason for rejection**: Rejected by author: same reason as C, plus the
    stack does not fit a terminal UI.

### E. Repo-first navigation (org -> repo -> PR -> runs)

*   **Pros**: browses any repo, not only PRs I touch.
*   **Cons**: several screens before reaching a PR; one `gh run list` call per
    PR on every poll; does not answer "what needs me?". This is the first
    attempt's design.
*   **Reason for rejection**: Rejected by author: one search per view finds my
    PRs across the org with one query.

### F. Python + Textual (first attempt's stack)

*   **Pros**: fast to write; existing code on `feat/python-mvp`.
*   **Cons**: the first attempt's UI was broken (focus, freezes); Python needs
    an environment to install; no reference project of this shape to follow.
*   **Reason for rejection**: Rejected by author: Go + Bubble Tea, with gh-dash
    as a working reference, single binary install.
*   **Exploration**: the author's notes on how cctop (Python + Textual) is
    built: [python-alternative.md](../python-alternative.md).

## Views

### G. One view for Review-requested and Involved, with a "why" column

*   **Pros**: one screen for all PRs by others; fewer views to switch.
*   **Cons**: the search does not say why a PR matched, so the "why" column
    needs extra queries; mixes "I must review" with "I was mentioned".
*   **Reason for rejection**: Rejected by author: separate views are cleaner,
    and each view is only a different query on the same table.

### H. Keep reviewed PRs in Review-requested (`reviewed-by:@me`)

*   **Pros**: shows PRs I reviewed until they close.
*   **Cons**: a second query per poll; differs from GitHub's own meaning of
    "review requested".
*   **Reason for rejection**: Rejected by author: follow GitHub's behavior;
    reviewed PRs drop out.

### I. Changed-row highlighting and acknowledge (pr-tracker feature)

*   **Pros**: shows what changed since I last looked.
*   **Cons**: needs a "last seen" state per row and an acknowledge flow.
*   **Reason for rejection**: Rejected by author: the running marks and a
    later activity sort cover the need.

## Refresh

### J. Faster GitHub poll while CI runs (2.5 minutes)

*   **Pros**: running builds show their result sooner without pressing `r`.
*   **Cons**: doubles GitHub budget use while anything runs; adds a second
    refresh mode.
*   **Reason for rejection**: Rejected by author: real time is not needed; one
    5-minute poll plus running marks and `r` is enough.

### K. Wait for a good GitHub fetch before refreshing Jira and Jenkins

*   **Pros**: one refresh path, simpler code.
*   **Cons**: a GitHub outage or rate limit freezes ticket and build state too.
*   **Reason for rejection**: Rejected by author: each source refreshes on its
    own, using the keys and jobs already known.

## Technical

### L. GitHub access through the `go-gh` library, or library for reads and `gh` for writes

*   See [0009-github-access.md](../decisions/0009-github-access.md).
*   **Reason for rejection**: Rejected by author for now: a `gh` subprocess is
    less code; the domain interfaces keep a later swap possible.

### M. YAML or a flat config file

*   See [config.md](./config.md).
*   **Reason for rejection**: Rejected by author: TOML preferred after
    comparing examples (no indentation rules, raw strings for regex).

### N. Plugin system for trackers and CI

*   **Pros**: other trackers and CI systems could be added without changing
    ghtop.
*   **Cons**: one tracker and two CI kinds exist; a plugin system is code and
    a contract to maintain with no second user.
*   **Reason for rejection**: Rejected by author: small internal interfaces
    with one implementation each.

### O. One large design document

*   **Pros**: everything in one place.
*   **Cons**: long to review in short sessions; large sections are hard to
    keep current.
*   **Reason for rejection**: Rejected by author: small linked files, one home
    per fact, with the design doc as the entry point.
