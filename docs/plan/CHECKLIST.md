# ghtop planning checklist

Reduced in the 2026-11-09 review (concepts_brief.md item 27): ghtop is a
personal tool, so planning stops at what an agent needs to start M1. Other
detail is written per milestone in `implementation.md` or the task prompt.

Rules:

- One home per fact: keys in `core/keymap.md`, config keys in `config.md`,
  commands in `services/github.md`, decisions in `concepts_brief.md`,
  structure and flows in `docs/architecture.md`. Other files link, never copy.
- Placeholders only: `example-org`, `EX-123`, `ci.example.com`. No real org data.
- A decision made in any session is added to `concepts_brief.md` in the same
  session. `docs/architecture.md` is updated in the same change as the code.

Status legend: `[ ]` not started, `[~]` draft, `[x]` done.

## Done

- [x] `brainstorm_context.md` - frozen Goldfish input
- [x] `concepts_brief.md` - brainstorm result and decisions (GitHub access
      folded in from 0009)
- [x] `DEFERRED.md` - deferred topics, curated by the author
- [x] `docs/designs/ghtop.md` - design doc
- [x] `alternatives.md` - paths not taken
- [x] `implementation.md` - file plan, milestones, constants, verification
      (revised 2026-11-09)
- [x] `core/keymap.md` - every key
- [x] gh-dash trial; fork or rewrite (new tool)
- [x] Old docs and `docs/decisions/` deleted (2026-11-09)

## Before M1

- [~] `services/github.md` - command list drafted 2026-11-09; filled in per milestone;
      search query per view, caps, the compare call for behind-by; check
      whether `mergeStateStatus` needs the `merge-info-preview` Accept header
- [x] M1 section of `implementation.md` - PR table: columns, shrink order,
      State, threads/comments, `s` sort toggle, glyphs, Row fields (2026-11-09)
- [x] `config.md` - keys settled; example checked against the Keys table
- [~] `docs/architecture.md` - matches the revised plan; update with code
