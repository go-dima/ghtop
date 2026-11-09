# ghtop: deferred topics

Topics we chose not to do now. The author curates this list: add, re-word,
promote to a phase, or drop. Each entry says why it waits and what would bring
it back.

Status: `waiting` (not planned), `next` (candidate for the next phase),
`dropped` (decided against; kept for the record).

| Topic | Status | Why it waits | Bring it back when |
|---|---|---|---|
| Fast Jenkins poll while builds run (Jenkins REST, no GitHub cost) | waiting | 5 min poll + manual refresh is enough; running builds are marked (decision #17) | builds finish and the screen lags noticeably |
| GitHub poll faster than 5 min while CI runs | waiting | real time not needed (decision #17) | manual refresh after a running mark gets tedious |
| In-app log viewer | waiting | biggest UI-complexity source in the old attempt; v1 opens logs in browser or `$PAGER` | failure summaries are not enough to act on |
| Jenkins Build Now with a parameter form | waiting | v1: no-parameter Build Now and config presets | presets are not enough |
| "Last updated" activity sort (`activityAt`) | waiting | needs check times in the query (cost) and is undefined across restarts | the default group sort hides changes I care about |
| Jira transitions that need fields (e.g. resolution) | waiting | v1 shows the error and opens the ticket | it happens often |
| Picker for PRs with several ticket keys | waiting | primary key rule first (decision #21) | the primary key is wrong often |
| Involved filter by `created` instead of `updated` | waiting | `updated` is the start (bot activity may keep PRs) | Involved view gets noisy |
| Closed PRs I reviewed (`reviewed-by:@me`) | waiting | Review-requested follows GitHub's behavior | I miss PRs I reviewed |
| Update branch by rebase | waiting | merge is the default; rebase rewrites the PR branch | a repo requires linear history |
| User-overridable keymap | waiting | personal tool, one keymap | someone else uses ghtop |
| Disk cache for a warm start | waiting | in-memory cache is enough | start-up feels slow |
| Multiple orgs | waiting | one org today | a second org shows up |
| Windows / WSL | waiting | macOS only | needed |
| Plugin system for trackers or CI | dropped | one tracker, two CI kinds; small interfaces are enough | a second tracker is real |
| Changed-row highlighting and ack | dropped | activity sort covers the need | |
| Emoji glyphs option | dropped | single-width symbols only (decision #23) | |
| Fork of gh-dash | dropped | new tool on the same stack (decision #8) | |
