# Hindsight

Local observability over Claude Code history for a solo skill-heavy operator: where tokens went, what was done, how the process ran. Read-only, stdlib-only Python over SQLite. Consolidated successor to ccwhere (shipped, superseded) and ccwhy's observability half — see `background/ideation/framing.md`.

## Visibility
**Born public.** This repo is the public repo — there is no private working copy and no
export step. Everything committed here is publishable from the first commit:

- The working record — `background/` (ideation, definition, design, tickets, the why) and
  `docs/adr/` — is public by design. Write it knowing that.
- Real session-derived data, fixtures drawn from it, unfiltered screenshots, secrets and
  machine paths never enter git. `local-data/` is ignored for the first; screenshots are
  taken from a filtered or synthetic view; issue bodies reference sessions by id, never
  quoted transcript text from another project. `eval/` fixtures are the one sanctioned
  exception and were reviewed for publication (ticket 087).
- Toolchain is plugins at user scope plus `~/.claude/skills/`; nothing under
  `.claude/skills/` is tracked here.
- `.githooks/pre-commit` refuses a commit that matches `.githooks/denylist.txt` (home
  paths, key shapes, transcript filenames). Add to the list; do not bypass it.

Issues live on this repo and are public. The private working repo this was built in is
`dempseydata/hindsight-old` — closed, kept for its history, never to be flipped.

## Phase layout
`background/ideation/` → `background/definition/` → `background/design/` → `build/`.
Context from earlier phases informs later ones — don't engage on design without reading the
definition, don't engage on build without reading the design decisions. `background/why.md`
is the story: why it was built, how, and what was reversed. `background/tickets/` is the
exported working tracker (88 tickets, closing comments included); GitHub's own numbering
on this repo starts afresh, so cite an exported ticket by its file, not `#N`.

## Process
This project deviates from the house pipeline. `.claude/my-process.md` wins where the two disagree.

@.claude/my-process.md

## Stack conventions
- Domain vocabulary → `CONTEXT.md`. Decision rationale → `docs/adr/`. Reviewability docs
  (`architecture`, `flows`, `permissions`, `variables`, `cron`, `automation`) → `docs/`,
  from `/document-app`.
- `diagnosing-bugs` and `improve-codebase-architecture` must read `CONTEXT.md` + `docs/adr/` first.
- `design/tokens.css` is the styling contract, inlined by `build/serve.py` at render time.
  Change a value there, never in a view. Root `DESIGN.md` is the shipped design system,
  re-derived from the built UI (ticket 052) — an output, not an input.

Pipeline map and house design standard: `~/Documents/Claude/my-standards/` (pipeline.md — there is no house DESIGN.md; a product's root `DESIGN.md`, if any, is derived from its shipped UI for Impeccable's drift detection, never a source of truth).

## Agent skills

### Issue tracker
Issues live in GitHub Issues at `dempseydata/hindsight` (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels
The five canonical defaults, label strings equal to role names. See `docs/agents/triage-labels.md`.

### Domain docs
Single-context: root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.

## Design skills
Direction is settled (ADR-0007, ADR-0008) — a new surface still runs the design flow in `my-process.md`, with the settled direction as an input. Pick ONE taste-skill style variant per candidate (`taste-skill:high-end-visual-design`, `taste-skill:minimalist-ui`, or `taste-skill:industrial-brutalist-ui` — from the `taste-skill@taste-skill` plugin, user scope, nothing copied into the repo); `impeccable` fine-tunes only after a direction is chosen.
