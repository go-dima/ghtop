# ghtop: my next tasks

The task at the top of "Next" is the one to do now. When it is done, move it to
"Done" with the date. Planning progress lives in `CHECKLIST.md`; this file
tracks what I (the author) have to do or decide.

## Next

1. **Install Go** (latest stable, `brew install go`) and `pre-commit`.
2. **Session: M1 detail.** Agent drafts the M1 section of `implementation.md`
   (columns per view, drop order at 120/80, unanswered definitions, glyphs,
   Row fields). I review.
3. **M1: read-only GitHub + framework check.**

## Waiting on

- Curate `DEFERRED.md` whenever a topic is pushed out.

## Done

- 2026-11-09: `services/github.md` drafted as a working command list (filled
  in per milestone); G2, G6 and G9 run against the real org. `config.md`
  example checked against the Keys table; quick-move fields, regex case and
  `jenkins.user` precedence defined.

- 2026-11-09: Plan review (Goldfish Stage 9 + over-engineering pass, log in
  `docs/reviews/2026-11-09-decisions.md`). Planning set reduced, 3 milestones, no CI,
  pre-commit hooks, concrete clients, ADR 0009 folded into the brief, old docs
  deleted. Decided: Merged uses `updated:>=`, org required, PR template kept
  (answers the PR-template question: yes), latest library versions. Branch
  plan: work on `feat/v2`, merge to `main`.

- 2026-11-08: Design doc finalized at `docs/designs/ghtop.md`; brief
  reconciled (decisions #25, #26).

- 2026-11-08: Keymap session: `Ctrl-A` action menu (`r` re-run, `b` Build
  Now, `u` update branch, `m` move ticket), `1`-`4` views, vim movement,
  `c`/`C` copy PR/ticket URL (dropped 2026-11-09). See `core/keymap.md`.

- 2026-11-08: Added the "update branch" action (merge base into PR branch when
  no conflicts; open PR page when conflicts).

- 2026-11-08: Brief approved. Decisions #21-#24 (primary ticket key, TOML
  config + Go regex case-insensitive, single-width glyphs, `DEFERRED.md`).

- 2026-11-08: Jira/Jenkins optional with an access check on start and on
  refresh; one 5 min poll with running marks (no faster poll); Actions run id via GraphQL; Jenkins trust
  rules in config; k9s-style confirm dialog.

- 2026-11-08: Review-requested and Involved moved to the first phase (same
  table, different query). Vim `j/k` navigation back (no clash with `t`).

- 2026-11-08: Brainstorm with Goldfish review; `concepts_brief.md` and
  `CHECKLIST.md` written.
- 2026-11-08: gh-dash trial; decided on a new tool on gh-dash's stack.
- 2026-11-08: Chose the full planning file set, with small agents per file.
- 2026-11-08: Keys fixed so far: `t` ticket, `b` Jenkins build (browser),
  `a` Actions run drill-down, `r` refresh.
- 2026-11-08: Added the Involved view (later phase) to the brief.
- 2026-11-08: Four separate views on one shared PR table; same columns
  everywhere; closed PRs 14 days.
- 2026-11-08: Review-requested follows GitHub (reviewed PRs drop out). Fetch
  only the active view; Review-requested also polled in the background.
- 2026-11-08: Merged = my PRs, 14 days. Involved = open PRs from the last 14
  days. Review-requested background poll = count only. View switch = cached
  rows, then refresh.
