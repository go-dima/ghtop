# ghtop brainstorm context (Goldfish input)

## Anchored hypothesis

ghtop is a new terminal TUI with k9s-style keyboard navigation. It shows the pull
requests of the user logged in to the `gh` CLI, in separate views (one view on
screen at a time):

- **Open PRs** authored by me.
- **Merged/closed PRs** from the last N days (default 14, configurable).
- **Review-requested PRs** (later phase).

Each row shows PR state, review state, CI state (GitHub Actions runs and Jenkins
builds, both discovered from the PR's checks), and the linked Jira ticket.

Actions on the highlighted row (or highlighted element in a drill-down):

- open PR / Jira ticket / CI build in browser (`o`, `j`, ...)
- transition the Jira ticket
- re-run a GitHub Actions run (mainly failed runs)
- Jenkins "Build Now" on the PR job, sometimes with parameters
- see why a run failed (scope of in-terminal log viewing is open)

Refresh: periodic poll (like pr-tracker: 5 min, 60 s cache) + manual refresh +
optional faster poll while CI is running (configurable). No changed-row
highlighting; instead a "last updated" sort that accounts for build status and
GitHub changes.

## Constraints

- Prerequisites: `gh` CLI (authenticated), `JENKINS_TOKEN` env var (Basic auth
  with a Jenkins user), `twg` CLI logged in for Jira (Atlassian CLI; must not use
  an MCP server, which can block on OAuth).
- Jira is the first issue tracker, but the tracker must be configurable/pluggable.
  Jenkins is optional/configurable. GitHub Actions is top priority.
- The repo `go-dima/ghtop` is public. All org-specific data (org name, Jira site,
  Jira key regex, Jenkins host/user, quick-move transitions) must live only in a
  private user config file. The repo holds only generic defaults.
- Co-exists with pr-tracker (a local web page with the same data). Shares ideas,
  not code. Different implementation.
- Tech stack is undecided; to be chosen in a separate "tech stack" document using
  reference tools as guides: k9s (Go + tview), gh-dash (Go + Bubble Tea, a gh
  extension with configurable PR sections and custom keybindings), cctop (a
  Python htop-like viewer of Claude processes), nat/ghtop (GitHub activity top).
- Previous attempt (Python + Textual, repo-centric org -> repo -> PR -> actions ->
  logs hierarchy) had a broken, buggy UI. The code may be fully replaced. The new
  design is user-centric (GitHub search for my PRs across the org).
- Row actions UX: user leans to flat rows (distinct keys) plus a drill-down
  detail view; final choice after visual mockups.

## Deliverable of this planning phase

No code. A set of planning files reviewed in gaps over several sessions:
a plan, ASCII mockups for each view, per-view specs, shared core logic
(data model, refresh, keymap), per-service specs (GitHub, Actions, Jenkins, Jira),
config spec, tech-stack decision, and a checklist of files to plan and review.

## Local reference files (read these; reviewers cannot open URLs)

pr-tracker (private local tool, not in this repo; working Node implementation of the same data, with known limits):

- <pr-tracker>/README.md
- <pr-tracker>/GUIDE.md
- <pr-tracker>/CLAUDE.md  (known problems section)
- <pr-tracker>/config.js
- <pr-tracker>/sources/README.md
- <pr-tracker>/sources/github.js  (GraphQL query, caps, rate-limit cost, closed-PR light query because full query hit GitHub's 10 s limit)
- <pr-tracker>/sources/jenkins.js  (403 without x-jenkins header = VPN off)
- <pr-tracker>/sources/jira.js  (twg calls, transitions)

Previous ghtop attempt (plans only on main):

- <ghtop repo>/ghtop.md
- <ghtop repo>/docs/ghtop-go.md
- <ghtop repo>/docs/ghtop-python-mvp.md
