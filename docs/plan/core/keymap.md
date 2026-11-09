# ghtop keymap

*   **Status:** Draft (keymap session done 2026-11-08; ready for review)
*   **Design doc:** [ghtop.md](../../designs/ghtop.md)

Legend: **fixed** = decided in the keymap session or earlier.

## Rule

Plain keys open or show things. Every action that changes something on
GitHub, Jenkins or Jira goes through the **action menu**: `Ctrl-A` ("action"),
then a letter, then the confirm dialog. The menu is titled with the target PR
and lists only the actions that apply now (for example no "update branch"
unless the PR is behind). **fixed**

Notes:

*   The menu shows its letters on screen, because `r` and `b` mean something
    else outside it (refresh, open Jenkins build).

*   `Ctrl-A` works in the table, the PR detail view and the Actions view. In
    the `/` filter and `:` command line it keeps its text-input meaning (start
    of line).
*   If a terminal multiplexer uses `Ctrl-A` as its prefix (screen, or tmux
    remapped), ghtop never sees it. Accepted by author.

## Global (every view)

| Key | Action | Status |
|---|---|---|
| `↑` `↓` / `k` `j` | move cursor | fixed |
| `PgUp` `PgDn` / `Ctrl-U` `Ctrl-D` | page up / down (vim: half page) | fixed |
| `Home` `End` / `g` `G` | first / last row | fixed |
| `Enter` | open PR detail view | fixed |
| `Esc` | back / close menu or dialog / clear filter | fixed |
| `r` | refresh now (skips cache, not the budget floor) | fixed |
| `/` | filter rows by text | fixed |
| `:` | command line (`:open`, `:merged`, `:review`, `:involved`, `:doctor`, `:q`) | fixed |
| `?` | help: every key for the current screen, including the action menu letters | fixed |
| `q` / `Ctrl-C` | quit | fixed |
| `1` `2` `3` `4` | switch view: Open, Merged, Review-requested, Involved (shown in the header) | fixed |

## Row: open and show (PR table and PR detail view)

| Key | Action | Status |
|---|---|---|
| `o` | open PR in browser | fixed |
| `t` | open primary ticket in browser | fixed |
| `b` | open Jenkins build in browser (picker if several jobs) | fixed |
| `a` | open Actions view (runs, jobs, failed steps) | fixed |
| `c` | copy PR URL to clipboard | fixed |
| `C` | copy primary ticket URL to clipboard | fixed |

## Action menu (`Ctrl-A`, then)

| Key | Action | Shown when | Status |
|---|---|---|---|
| `r` | re-run failed jobs of the latest failed Actions run (in the Actions view: of the selected run) | a completed run has failed jobs | fixed |
| `b` | Jenkins Build Now (picker for job and preset) | Jenkins available and a job matches the trusted pattern | fixed |
| `u` | update branch (merge base in); with conflicts: open PR page | PR is behind; not while GitHub has not computed the state | fixed |
| `m` | move ticket by the configured quick move | tracker available and a quick move matches the ticket status | fixed |
| `?` | help for the menu | always | fixed |
| `Esc` | close the menu | always | fixed |

## Actions view (`a`)

| Key | Action | Status |
|---|---|---|
| `↑` `↓` / `k` `j` | move between runs and jobs | fixed |
| `Enter` | expand run -> jobs -> failed steps | fixed |
| `o` | open the selected run or job in browser | fixed |
| `Ctrl-A` `r` | re-run failed jobs of the selected run | fixed |
| `Esc` | back to the table | fixed |

## Picker and confirm dialog

| Key | Action | Status |
|---|---|---|
| `↑` `↓` / `k` `j` | move in picker | fixed |
| `Enter` | choose / press the selected button | fixed |
| `←` `→` / `Tab` | move between Cancel and OK (Cancel selected first) | fixed |
| `Esc` | cancel | fixed |

## Notes for implementation

*   `Tab` is not used in the table (kept free, for example for focus inside
    the PR detail view); it moves between Cancel and OK in the confirm dialog.
*   Copy (`c`, `C`) writes to the clipboard with the OSC 52 terminal sequence,
    which also works inside tmux and over SSH, and falls back to `pbcopy` on
    macOS. The status bar confirms what was copied.
*   The help overlay (`?`) and the README key list are generated from this
    keymap's code, so they cannot drift from it.
