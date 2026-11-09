# ghtop planning checklist

Files to plan and review, in dependency order. Work through them in separate
sessions; tick a box when the file is reviewed.

Rules for every file:

- Specs are stack-neutral, except `stack/` and `docs/architecture.md`
  (stack is decided: Go + Bubble Tea, see D-001).
- Small files, linked. One home per fact (status enum in
  `core/data-model.md`, keys in `core/keymap.md`, intervals in
  `core/refresh.md`). Other files link to it, never copy. When a section grows
  past what one review session covers, split it into its own file and link it.
- Placeholders only: `example-org`, `EX-123`, `ci.example.com`. No real org data.
- Each file starts with `Status: draft | reviewed | frozen` and an
  "Open questions" list.
- A decision made in any session gets a file in `docs/decisions/` in the same
  session.
- One small agent per file (draft or edit). Its prompt includes:
  `concepts_brief.md`, these rules, the files listed as its dependencies, and
  the placeholder data set. The author reviews the result before the box is
  ticked.

Status legend: `[ ]` not started, `[a]` approved (not written yet),
`[~]` draft, `[x]` written.

## Long-lived docs (kept in the repo after planning)

- [a] `docs/decisions/README.md` - how to add a decision, index of decisions
- [a] `docs/decisions/NNNN-<title>.md` - one file per decision: context,
      decision, alternatives, consequences. First ones:
  - [a] 0001 Write a new tool on gh-dash's stack (Go + Bubble Tea), not a fork
  - [a] 0002 User-centric views (Open, Merged, Review-requested, Involved)
  - [a] 0003 Separate tool from pr-tracker; ideas only
  - [a] 0004 Jira through `twg`; Jenkins optional; Actions first
  - [a] 0005 Organization data private; public repo has placeholders only
  - [a] 0006 Arrows + vim `j/k` navigation, own keymap; `t` ticket,
        `b` Jenkins build, `a` Actions drill-down, `r` refresh
  - [a] 0007 Fast polling deferred; when added, it polls Jenkins, not GitHub
  - [a] 0008 Architecture diagrams in Mermaid, kept in the repo
  - [~] 0009 How ghtop calls GitHub: `gh` subprocess behind domain
        interfaces, closed command list (accepted; file drafted)
- [~] `docs/architecture.md` - technical plan + Mermaid diagrams (moved out of
      the design doc), updated in the same change as
      the code they describe:
  - [~] context: ghtop, `gh`, GitHub API, `twg`/Jira, Jenkins, browser, config
  - [~] components: views, core (model, refresh, keymap, actions, errors),
        services (GitHub, Actions, Jenkins, Jira)
  - [~] data flow: one refresh, from queries to rendered rows
  - [a] sequence: one action (for example re-run failed Actions run) with
        confirm and result

## Phase 0: inputs

- [x] `brainstorm_context.md` - frozen Goldfish input
- [x] `concepts_brief.md` - brainstorm result (approved 2026-11-08)
- [x] `DEFERRED.md` - deferred topics, curated by the author
- [~] `alternatives.md` - paths not taken, linked from the design doc
- [~] `implementation.md` - file-by-file plan, milestones, verification
- [x] gh-dash trial (verdict in `concepts_brief.md`)
- [x] Fork or rewrite: new tool, gh-dash stack (-> decision 0001)
- [ ] Root cause of the old UI bugs (in the design doc)

## Phase 1: frame

- [ ] `README.md` - index, reading order, status of each file
- [x] `docs/designs/ghtop.md` - design doc (finalized 2026-11-08): the single source for goals, MVP,
      non-goals, architecture, alternatives and file plan (replaces
      `00-plan.md`; other files link to it, never copy it)
- [ ] `01-glossary.md` - Row, View, Check, CIProvider, Tracker, Action,
      activityAt, Target

## Phase 2: data, then mockups (settles flat row vs drill-down)

- [ ] `core/data-model.md` - PR row, check, ticket, status enum, glyph table
      (ASCII + emoji), worst-state order, activityAt, roles
- [ ] `services/_contract.md` - Tracker and CIProvider interfaces, capability
      flags, how a check is classified as Actions / Jenkins / other
- [ ] `views/_layout.md` - header, source health strip, status bar, view
      switching, mockup width, placeholder data set
- [ ] `views/pr-table.md` - the one PR table all views share: mockups (2-3
      variants: flat, flat + drill-down, grouped), columns, sort, keys,
      empty/error states
- [ ] `views/open-prs.md` - data source only, plus anything that differs
- [ ] `views/merged-prs.md` - data source (`merged:` vs `updated:`), lighter
      data for closed PRs
- [ ] `views/pr-detail.md` - drill-down: checks list, tickets, per-element
      actions, pickers (gh-dash PR view as reference)
- [ ] `views/actions-run.md` - `a` drill-down: workflow runs, jobs, state,
      failed steps; REST fetch on open; open-in-browser as a second step
- [ ] `views/failure-reason.md` - v1: failed checks + summaries + open log;
      later: in-app log
- [ ] `views/review-requested.md` - phase 1, data source only;
      `review-requested:@me` as GitHub returns it; background count-only
      query feeds a header count; rows fetched on view switch
- [ ] `views/involved.md` - phase 1, data source only;
      `involves:@me -author:@me is:open updated:>=<14 days ago>`; closed
      hidden; `updated` chosen as the start

## Phase 2b: UI spike (small code sample, thrown away or kept as seed)

- [ ] `spike/README.md` - scope: one table from one GraphQL search, arrow keys,
      `o` open PR, `r` refresh, resize; what we learned (focus, resize,
      refresh while moving the cursor)

## Phase 3: behavior

- [~] `core/keymap.md` - go over every key together; arrows + `j/k` for movement;
      fixed: `t` ticket, `b` Jenkins, `a` Actions, `r` refresh; pick the re-run key;
      global keys, per-view keys, reserved keys, `:` commands
- [ ] `core/actions.md` - each action: target, preconditions, confirm style,
      provider call, result/feedback
- [ ] `core/refresh.md` - active view only + Review-requested count in the
      background; view switch shows cached rows with age, then refreshes;
      slow poll + manual refresh, cache TTL, budget limit,
      cursor anchoring on re-sort; fast Jenkins poll as a later phase
- [ ] `core/errors.md` - error classes -> UI surface, retry, stale marking;
      `--debug` log; `ghtop doctor`

## Phase 4: services (deltas from pr-tracker, placeholders only)

- [ ] `services/github.md` - the closed list of `gh` commands (with
      placeholders; doubles as a manual smoke test), search queries per view,
      caps, light closed query,
      rate-limit reading
- [ ] `services/github-actions.md` - run id source, re-run failed jobs, failure
      summary
- [ ] `services/jenkins.md` - URL trust rules, live state, Build Now, queue
      follow, parameters, crumb fallback, later: fast poll of running builds
- [ ] `services/jira-twg.md` - key extraction, fetch, transitions, quick moves,
      key validation, twg version

## Phase 5: config

- [~] `config.md` - (format examples drafted) versioned schema, path and precedence, public defaults vs
      private file, env secrets, validation, example file with placeholders,
      leak guard

## Phase 6: ready-to-code gate

- [ ] Every file above `reviewed`
- [ ] `docs/architecture.md` matches the specs
- [ ] Leak grep over `docs/` returns 0 hits
- [ ] MVP acceptance criteria agreed (in the design doc)
- [ ] Old docs moved to `docs/archive/` with a "superseded" note
- [ ] Branch plan: work on `plan/v2` and merge to `main`, or reset `main`
