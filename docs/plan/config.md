# ghtop config

*   **Status:** Draft (format examples; full schema later)
*   **Decided:** TOML at `~/.config/ghtop/config.toml`, Go regex matched
    case-insensitively (brief decision #22). Placeholders only in this file.

## Example: TOML (chosen format)

```toml
version = 1

[github]
org = "example-org"
closed_days = 14
involved_days = 14
poll = "5m"
budget_floor = "20%"

[tracker]
kind = "jira"
site = "example.atlassian.net"
key_pattern = 'EX-\d+'          # Go regex, matched case-insensitively

[[tracker.quick_moves]]
from = "In Progress"
to = "Code Review"

[[tracker.quick_moves]]
from = "Code Review"
to = "Done"
transition = "Resolve"
only_when_merged = true

[jenkins]
user = "${JENKINS_USER}"
hosts = ["ci.example.com"]
job_pattern = '^/job/[^/]+/job/PR-\d+/$'
follow_queue = true

[[jenkins.presets."example-repo_x86"]]
name = "default"
params = {}

[[jenkins.presets."example-repo_x86"]]
name = "release"
params = { BUILD_TYPE = "Release" }

[ui]
glyphs = "unicode"                # single-width symbols only
strip_key_from_title = false      # opt-in: remove a leading ticket key
```

What the example shows:

*   Tables match providers (`[github]`, `[tracker]`, `[jenkins]`), so turning
    a provider off means leaving its table out.
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
*   Durations and percentages are strings (`"5m"`, `"20%"`) that ghtop parses.

## Alternative: YAML

```yaml
version: 1

github:
  org: example-org            # required; ghtop refuses to start without it
  closed_days: 14             # Merged view window
  involved_days: 14           # Involved view window (by last update)
  poll: 5m                    # one interval for every view
  budget_floor: 20%           # skip scheduled polls below this share left

tracker:                      # optional; ghtop runs without it
  kind: jira
  site: example.atlassian.net
  key_pattern: 'EX-\d+'      # Go regex; single quotes keep \d as is
  quick_moves:
    - from: In Progress
      to: Code Review
    - from: Code Review
      to: Done
      transition: Resolve     # needed when several transitions reach "Done"
      only_when_merged: true

jenkins:                      # optional; token comes from JENKINS_TOKEN
  user: ${JENKINS_USER}       # or a literal; never the token
  hosts:
    - ci.example.com          # exact host match; https only
  job_pattern: '^/job/[^/]+/job/PR-\d+/$'   # Build Now only on these paths
  follow_queue: true
  presets:                    # Build Now parameter presets, by job name
    example-repo_x86:
      - name: default
        params: {}
      - name: release
        params:
          BUILD_TYPE: Release

ui:
  glyphs: unicode             # single-width symbols only
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
*   Rejected by author. Against: no clear way to switch a provider off (which keys belong to it?),
    and quick moves and presets still need nesting.

## Open points

*   Should `${VAR}` expansion be allowed anywhere, or only in `jenkins.user`?
*   Preset key: Jenkins job name, or the job URL path?
