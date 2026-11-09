# ghtop: my next tasks

The task at the top of "Next" is the one to do now. When it is done, move it to
"Done" with the date. File-level progress lives in `CHECKLIST.md`; this file
tracks what I (the author) have to do or decide.

## Next

0. **Review the design doc** with `/egm:egm-review docs/designs/ghtop.md`
   (fresh-context Goldfish review).
1. **Install Go** (latest stable, `brew install go`) before the UI spike.
2. **Pick the branch plan.** Work on a `plan/v2` branch and merge to `main` when
   planning is done, or commit straight to `main`. The planning files are
   untracked until then.
3. **Write down what broke in the old UI.** A few lines from memory: which
   screens, what happened (freeze, lost focus, wrong row, slow), when. Goes into
   the design doc.
4. **Answer: PR-template checkbox for diagrams?** A "diagrams updated" checkbox
   in the PR template, to keep `docs/architecture.md` in step with the code.
5. **Session: frame.** Agents draft `README.md`,
   `01-glossary.md` and decisions 0001-0008. I review each.
6. **Session: data.** Agents draft `core/data-model.md` and
   `services/_contract.md`. I review.
7. **Session: mockups.** Agents draft `views/_layout.md` and the view files
   with 2-3 mockup variants each. I pick flat row vs drill-down.
8. **Session: UI spike.** Small code sample; record what we learned in
   `spike/README.md`.
9. **Sessions: behavior, services, config.** In `CHECKLIST.md` order.
10. **Ready-to-code gate** (`CHECKLIST.md` Phase 6).

## Waiting on

- Curate `DEFERRED.md` whenever a topic is pushed out.

## Done

- 2026-11-08: Design doc finalized at `docs/designs/ghtop.md`; brief
  reconciled (decisions #25, #26).

- 2026-11-08: Keymap session: `Ctrl-A` action menu (`r` re-run, `b` Build
  Now, `u` update branch, `m` move ticket), `1`-`4` views, vim movement,
  `c`/`C` copy PR/ticket URL. See `core/keymap.md`.

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
