# ghtop config

*   **Status:** Reviewed 2026-11-09 (check the example against the Keys table
    before M1)
*   **Decided:** TOML at `~/.config/ghtop/config.toml` (or `--config <path>`),
    Go regex matched case-insensitively (brief decision #22). No `version`
    key, no `${VAR}` expansion, no other lookup paths. Placeholders only in
    this file.

## Example: TOML (chosen format)

```toml
[github]
org = "example-org"               # required; ghtop refuses to start without it
closed_days = 14                  # Merged view window
involved_days = 14                # Involved view window

[tracker]
enabled = true
site = "example.atlassian.net"
key_pattern = 'EX-\d+'           # Go regex, matched case-insensitively
status_order = ["In Progress", "Code Review", "QA", "Done"]

[[tracker.quick_moves]]
from = "In Progress"
to = "Code Review"

[[tracker.quick_moves]]
from = "Code Review"
to = "Done"
transition = "Resolve"
only_when_merged = true

[jenkins]
enabled = true
user = "jenkins-user"             # or leave out and set JENKINS_USER
hosts = ["ci.example.com"]
job_pattern = '^/job/[^/]+/job/PR-\d+/$'

[ui]
refresh = "5m"
glyphs = "unicode"                # single-width symbols only
strip_key_from_title = false      # opt-in: remove a leading ticket key
```

## Keys

| Key | Type | Default | Notes |
|---|---|---|---|
| `github.org` | string | required | refuse to start without it |
| `github.closed_days` | int | 14 | Merged view window; minimum 1 |
| `github.involved_days` | int | 14 | Involved view window; minimum 1 |
| `tracker.enabled` | bool | false | Jira on/off |
| `tracker.site` | string | required if enabled | `example.atlassian.net` |
| `tracker.key_pattern` | regex | required if enabled | Go regex, case-insensitive |
| `tracker.status_order` | list of strings | `[]` | ticket status order in the sort; unknown statuses last |
| `tracker.quick_moves` | list of `{from, to, transition?, only_when_merged?}` | `[]` | used by `Ctrl-A` `m` |
| `jenkins.enabled` | bool | false | Jenkins on/off |
| `jenkins.user` | string | `$JENKINS_USER` | the token comes only from `JENKINS_TOKEN` |
| `jenkins.hosts` | list of strings | required if enabled | exact hosts, no scheme, https only |
| `jenkins.job_pattern` | regex | required if enabled | path of PR jobs allowed for Build Now |
| `ui.refresh` | duration | `"5m"` | the one poll interval; minimum `1m` |
| `ui.glyphs` | `"unicode"` or `"ascii"` | `"unicode"` | single-width only |
| `ui.strip_key_from_title` | bool | false | |

"Ready to merge" is not configured: it comes from GitHub's `reviewDecision`
and `mergeStateStatus` (see implementation.md, file 14).

What the example shows:

*   Tables match sources (`[github]`, `[tracker]`, `[jenkins]`); `enabled`
    turns Jira or Jenkins on or off in one line.
*   Secrets never appear: `JENKINS_TOKEN` is read from the environment only.
*   Single-quoted strings are raw, so regex is written as is (`'EX-\d+'`).
*   Key patterns use a fixed prefix. A generic pattern such as
    `[A-Z][A-Z0-9]+-\d+`, matched case-insensitively, also matches `utf-8`,
    `sha-256` and `x86-64`.
*   PR titles are shown as written; `strip_key_from_title = true` removes a
    ticket key only at the start of the title (`EX-1: Fix x` -> `Fix x`), never
    in the middle.

TOML costs to keep in mind:

*   Lists of tables (`[[tracker.quick_moves]]`) repeat their header for every
    item, so long lists get long.
*   Durations are strings (`"5m"`) that ghtop parses.

## Alternative: YAML

Format comparison: the TOML example above written in YAML.

```yaml
github:
  org: example-org            # required; ghtop refuses to start without it
  closed_days: 14             # Merged view window
  involved_days: 14           # Involved view window

tracker:
  enabled: true
  site: example.atlassian.net
  key_pattern: 'EX-\d+'      # Go regex, matched case-insensitively
  status_order: [In Progress, Code Review, QA, Done]
  quick_moves:
    - from: In Progress
      to: Code Review
    - from: Code Review
      to: Done
      transition: Resolve
      only_when_merged: true

jenkins:
  enabled: true
  user: jenkins-user          # or leave out and set JENKINS_USER
  hosts:
    - ci.example.com
  job_pattern: '^/job/[^/]+/job/PR-\d+/$'

ui:
  refresh: 5m
  glyphs: unicode             # single-width symbols only
  strip_key_from_title: false # opt-in: remove a leading ticket key
```

*   For: shorter nested lists and maps; k9s, gh-dash and `gh` use YAML.
*   Against: indentation rules (no tabs), regex in double quotes needs every
    `\` doubled, and some parsers turn unquoted `no`/`on`/`off` into booleans.
*   Rejected by author: TOML preferred after comparing the two examples.

## Alternative: flat file (like pr-tracker's `config.js`)

```yaml
version: 1
org: example-org
closed_days: 14
jira_site: example.atlassian.net
jira_key_pattern: '[A-Z][A-Z0-9]+-\d+'
jenkins_hosts: [ci.example.com]
jenkins_job_pattern: '^/job/[^/]+/job/PR-\d+/$'
```

*   For: shortest file; matches pr-tracker's flat `config.js`.
*   Rejected by author. Against: no clear way to switch a provider off
    (which keys belong to it?), and quick moves still need nesting.

## Open points

None. (`${VAR}` expansion and Jenkins presets were dropped in the 2026-11-09
review; Build Now with parameters is in DEFERRED.md.)
