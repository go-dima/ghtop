# ghtop plan review: decision log

Status: applied 2026-11-09. The decisions in this file are the record of the
review.
Sources: `implementation_readiness_report.md` (Stage 9),
`implementation_readiness_report_r2.md` (round 2 re-audit),
`goldfish_review_report.md` (verdicts) and `overengineering_review.md` (15
cuts, walked through one at a time). These were working files and were
deleted after the review.

## 1. Cut decisions

| # | Cut | Decision |
|---|---|---|
| 1 | Spec files and review gate | **Modified.** Keep one spec: `services/github.md` with the explicit command list (`gh`, plus the few `twg` commands). Drop all other planned specs, the per-file review gate, `01-glossary.md`, `views/_layout.md` and the mockup variants. When a milestone needs detail, put it in `implementation.md` or the task prompt. |
| 2 | ADRs, PR template, architecture sync | **Modified.** Keep `architecture.md` (flows and diagrams) and the sync rule; file 48 stays. Keep the PR template (file 11) for agents. Its checkboxes are "architecture.md updated if structure changed" and "decision recorded in concepts_brief.md". Drop file 49 (ADR README and 0001–0008). Fold `0009-github-access.md` into `concepts_brief.md`, delete `docs/decisions/`, and repoint every link. |
| 3 | Archive old docs | **Accepted.** Delete `ghtop.md`, `docs/ghtop-go.md`, `docs/ghtop-python-mvp.md` and `docs/python-alternative.md`. Repoint `alternatives.md:70` to branch `feat/python-mvp`. Remove the CHECKLIST archive item. |
| 4 | Milestones | **Modified.** Three milestones; the spike folds into M1 (table below). Drop file 52 (`spike/`). Framework findings go in a "Framework notes" section of `implementation.md`. |
| 5 | CI, coverage, snapshots | **Accepted.** Drop file 10 (CI), the coverage targets, the UI snapshots, M8 and M14. Tests cover only: store sort/merge/cursor anchoring, Jira key extraction, Jenkins `Match`, `gh` stderr → hint mapping, and the refresh-while-moving scenario at model level if feasible. |
| 6 | Hooks | **Modified → pre-commit tool.** File 9 becomes `.pre-commit-config.yaml`, with the generic hooks, gofmt, go vet, `go test` (pre-push) and the leak guard (separate denylist file `~/.config/ghtop/leakguard.txt`). Drop `scripts/leakcheck.sh`, `.githooks/`, `make hooks`, `make leakcheck` and M10. Verification: `pre-commit run --all-files`. Check the `pre-commit-hooks` tag before writing the file. |
| 7 | Makefile, lint, `--version` | **Modified.** Drop the Makefile (file 7). Keep golangci-lint as a pre-commit hook, with `.golangci.yml` (file 8) adding `gosec` and `errcheck` to the defaults. Keep `--version` via `runtime/debug.ReadBuildInfo`; this replaces N6's ldflags. |
| 8 | Smoke | **Accepted.** Drop `make smoke` and the smoke test. Keep the command list in `services/github.md` for running commands by hand. Verification: "after a `gh`/`twg` upgrade, run `ghtop --debug` and check the log for non-zero exits". |
| 9 | Config machinery | **Accepted.** Path is `~/.config/ghtop/config.toml` or `--config`. Keep: unknown-key errors and validation (regexes compile, hosts have no scheme, org required (provisional)); the file is never written. Drop: `GHTOP_CONFIG`, XDG lookup, the `version` key, old-YAML detection and `${VAR}`. `JENKINS_USER` comes from env or a plain config value. File 14 tests: valid, minimal, missing org, bad regex, unknown key. |
| 10 | doctor, health, versions | **Accepted.** Drop the `doctor` subcommand, `:doctor` and the minimum-version checks. Keep the availability check at start and on `r`. implementation.md:31 becomes "tested with `gh` 2.103.3, `twg` 1.3.8". Verification uses the header instead of doctor. |
| 11 | Errors, redaction | **Accepted.** Keep 3 hints: auth expired, "VPN off?" and rate limited. Everything else shows the last stderr line or the HTTP status. Keep the cap warning and `SourceState`. The debug log never records headers or bodies, so there is no redaction code. File 25 tests pin only those 3 strings. |
| 12 | Budget | **Accepted.** Show `rateLimit.remaining` in the header. Drop the floor, the cap, M12, the budget verification and the `r`-vs-floor decision. Reword the design-doc goal. keymap.md:36 `r` becomes "refresh now (skips cache)". |
| 13 | Interfaces | **Concrete only.** Concrete clients: `github.Client`, `actions.Client`, `jenkins.Client`, `jira.Client`. `proc.Runner` is the only interface. Drop `internal/tracker/tracker.go`; key extraction becomes a function in the jira package. Drop M1. The 0009 consequence becomes "domain-level methods; add an interface when a second implementation exists". |
| 14 | Jenkins Build Now | **Modified.** Keep the job picker. Build Now POSTs without parameters (job defaults); if the job has no parameters, use `/build` (check on the first real call). Check the queue item at 10 s and at 20 s, then rely on refresh. Drop the `follow_queue` key, the crumb retry, presets, the preset picker and the preset-key decision. New DEFERRED entry: "Build Now with parameters, read from the job's parameter definitions". Reword CUJ 3. |
| 15 | Process runner | **Accepted.** Constants `maxProcs = 4` and a 30 s timeout per call. Keep no-shell, the env vars, cancel and the debug line. File 20: keep the fake runner and the timeout/cancel tests; drop the cap test. |

### Milestones after cut 4

| # | Milestone | Ends with |
|---|---|---|
| M1 | Read-only GitHub + framework check | Charm version chosen; config, `gh` runner, all 4 views, header (source state, remaining budget, review-requested count), status bar, help, pre-commit hooks, `--debug`, `--version`. Exit check: resize, focus, and a refresh arriving while the cursor moves all behave correctly. |
| M2 | Jira + Jenkins state | key extraction, ticket column, `t`, Jenkins URL trust, last-build state, `b` (with job picker), availability flags, "VPN off?" |
| M3 | Detail + actions | PR detail, Actions view (`a`), `Ctrl-A` menu, confirm dialog, re-run failed, update branch, Build Now (job picker, 10 s/20 s checks), quick move, `c`/`C`, `:` command line |

## 2. Remaining Stage 9 findings after the cuts

You have not given verdicts on these yet. Each row shows what is left after the cuts.

| ID | After cuts | Proposed action |
|---|---|---|
| B1 missing specs | Mostly moot. One spec left to write: `services/github.md`. `config.md` needs its keys and defaults completed. | Replace the B1 "Before coding starts" table with a 3-line note: before M1, write `services/github.md` and finish `config.md`; other detail goes in milestone sections or prompts. |
| B2 open decisions | Closed by the cuts: leak guard (6), `${VAR}` (9), preset key (14), PR template (2), `r` vs floor (12). | The "Decisions still needed" list shrinks to: Merged filter (files 22, 23), org filter (13, provisional "required"), Charm version (start of M1), behind-by query shape (21, 23), old-UI root cause (M1 exit check). Close the matching open questions in the design doc. |
| B3 PR template | Closed; the template is kept. | Fix the file 11 text (new checkbox wording, no "drop if no"). |
| B4 Charm version | Kept. | Chosen at the start of M1 and recorded in `go.mod` and `concepts_brief.md`. |
| M1 interface sync | Withdrawn (cut 13). | Update architecture.md with concrete type names under the sync rule. |
| M2 query passing | Half kept. | Queries are embedded and passed inline as `-f query=<text>`. |
| M3 config schema | Shrinks (cut 9). | `config.md` lists every remaining key with type and default. |
| M4 numbers | Answered by cuts 14 and 15. | Health check probes every configured Jenkins host. |
| M5 sort rule | Kept. | The "ready" rule and the ticket status order come from config. |
| M6 milestone map | Withdrawn (cut 4). | n/a |
| M7 features with no file | Kept, minus doctor. | Add `internal/ui/menu.go` and `internal/ui/cmdline.go` (`:open`, `:merged`, `:review`, `:involved`, `:q`), and `internal/platform/{open,clipboard}.go` running through `proc.Runner`. |

Your earlier verdicts still apply, adjusted by the cuts:
- **M9:** query file names, the tracker testdata prefix, and drop file 51. The ADR and test-file naming parts are moot.
- **M11:** behind-by is listed as a decision.
- **M13:** deletion replaces archiving.
- **N1–N5, N7, N8, N10–N12:** as proposed.
- **N6:** replaced by cut 7.
- **N9:** use "the user".
- **Added:** branch `feat/v2` replaces `plan/v2` in TASKS.md and CHECKLIST.md.

## 3. Files that will change

- **Edit:**
  - `docs/plan/implementation.md`: most of the changes.
  - `docs/designs/ghtop.md`:
    - open questions
    - budget goal
    - CUJ 3
    - Technical Plan link to 0009
    - implementation section
  - `docs/architecture.md`:
    - concrete types
    - no floor, no crumb, no presets
    - links
  - `docs/plan/concepts_brief.md`: gains the 0009 section and the amended item 15 and decisions.
  - `docs/plan/config.md`:
    - no `version`
    - no `${VAR}`
    - no presets or `follow_queue`
    - no `budget_floor`
    - keys and defaults
  - `docs/plan/core/keymap.md`: `r`, `:doctor`.
  - `docs/plan/CHECKLIST.md`: shrunk.
  - `docs/plan/TASKS.md`: branch, tasks 4/5–10.
  - `docs/plan/DEFERRED.md`: Build Now parameters.
  - `docs/plan/alternatives.md`: link.
- **Delete:** `ghtop.md`, `docs/ghtop-go.md`, `docs/ghtop-python-mvp.md`, `docs/python-alternative.md`, `docs/decisions/0009-github-access.md` (after folding it in).

## 4. Stage 9 round 2 (re-audit): Nits

Source: `implementation_readiness_report_r2.md` (deleted after the review). Walked through one at a time.

| # | Decision |
|---|---|
| N1 | M1 classifies checks as Actions or "other"; Jenkins via `jenkins.Match` arrives in M2. |
| N2 | `Search` returns `rateLimit{remaining, resetAt}`, not cost. |
| N3 | `closed.graphql` requests `state`, `merged`, `mergedAt`, `closedAt`. |
| N4 | Debug log: args are logged (org, search text, JQL), never headers/bodies/tokens; file 0600, dir 0700. |
| N5 | Skipped: child processes keep inheriting `JENKINS_TOKEN`. |
| N6 | Leak guard: blank lines skipped, public GitHub user not in the denylist, `verbose: true`, also runs at `commit-msg`. |
| N7 | `ui.refresh` >= 1m, `*_days` >= 1. |
| N8 | Merged stays `updated:>=`. |
| N9 | Design doc: only `Ctrl-A` actions are confirmed. |
| N10 | CUJ 3: Build Now is `Ctrl-A` `b`. |
| N11 | File 48 dropped (deletion already done). |
| N12 | Decision log moved here; EGM reports gitignored and deleted after the review. |
| N13 | implementation.md status "Reviewed 2026-11-09". |
| N14 | "Written against" `gh`/`twg` versions. |
| N15 | `--version` falls back to `vcs.revision` (+ `-dirty`). |
| N16 | No parse tests (cut 5 test scope); claim removed from file 21. |
| N17 | Old-UI root cause closed: candidates are the M1 exit check. |
| N18 | Four wording fixes in implementation.md. |
| N19 | Design doc implementation section is link-only; EGM footer dropped. |
| N20 | Stale brief/alternatives lines edited in place. |
| N21 | Build Now reads `parameterDefinitions` first, then `buildWithParameters` or `/build`. |
| N22 | Jenkins probe `GET /api/json?tree=mode` with three outcomes. |

## 5. Stage 9 round 2 (re-audit): Majors

| # | Decision |
|---|---|
| R1/R2 | Copy (`c`/`C`) dropped; no stdin needed in the runner. Browser opener uses detached `Runner.Start` (WaitDelay, outside the cap). |
| R3 | `-f` for all strings; `-F` only for ghtop's own numbers/booleans. |
| R4 | Partial GraphQL errors: use `data`, warn with `errors`; fail only without `data`; one fixture + test. |
| R5 | Queue URL rebuilt from configured host + parsed queue id; no id -> 'queued'; no test. |
| Drift | config.md YAML example and brief §8 aligned with item 27 (no follow_queue, presets, ${VAR}, crumb). |
| R6 | Behind shown from M1 via one REST compare per open PR (active view, not Merged); behind.graphql dropped. |
| R6 follow-up | Design doc: "the old 10 s per-PR `gh run list` poll is designed out". |
| R6 follow-up | Compare calls use the REST core quota (5000/hour), far below the limit at 5 min; not shown in the header. |
| R6 follow-up | Compare path segments path-escaped by ghtop (`/` in branch names kept); plain GET, no `-f` fields. |
| R7 | Results tagged by view; in-flight per (source, view); leaving a view keeps its fetch; quit cancels all. |
| R8 | M1 detail step tracked in CHECKLIST and TASKS. |
| R7 follow-up | Brief item 13: a fetch started before leaving a view still completes into its cache; only the view on screen is polled. |
| R9 | CI->sort group map (failure/unstable failed; success or no checks ok; running/aborted/unknown rest); cursor fallback = same index, clamped. |
| R10 | File ref 38->37; go-gh swap touches github + actions; golangci v2 config with gosec, one G204 nolint in the runner. |
| R11 | M1 exit check made measurable (4 checks). |
