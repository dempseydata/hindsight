---
stages:
  - name: Ideate
    commands: [brainstorm, discover, red-team-prd, pre-mortem, grill-me]
    paths: [background/ideation/, background/definition/]
  - name: Design
    commands: [design-sync, impeccable]
    paths: [background/design/, design/]
  - name: Plan
    commands: [grill-with-docs, to-spec, to-tickets, setup-matt-pocock-skills]
    skills: [grilling, domain-modeling, research, prototype]
    paths: [docs/adr/, CONTEXT.md]
  - name: Build
    commands: [implement, code-review, ponytail-review, diagnosing-bugs, ponytail-audit]
    skills: [tdd, code-review]
    paths: [build/, eval/]
  - name: Release
    commands: [security-preflight, graphify, document-app]
---
# my-process — this project's deviations from the house pipeline

`my-standards/pipeline.md` is the house default and carries the full phase routing, hard rules and toolchain. Where this file disagrees with it, **this file wins for this project**. Everything it doesn't mention follows the house pipeline unchanged.

The frontmatter above is the **process declaration** the how-view reads (ADR-0011): a stage is named, its commands and skills are what the trail attributes to it, its paths are where its artifacts land. Edit it when the process changes; the view re-reads it on the next analysis run.

## Phase folders

This repo is born public, so the record lives under `background/` — `background/ideation/` → `background/definition/` → `background/design/` → `build/` — with the exported tickets in `background/tickets/` and the story in `background/why.md`. The house default's bare `ideation/`, `definition/`, `design/` are the private-repo layout and do not apply here; `design/` at the root holds only `tokens.css`, the styling contract.

## Design: this project

Direction: **settled** — V3 · Indigo deck, chosen comparatively through
[Diverge 034](../background/tickets/034-diverge-five-candidate-directions.md) →
[Narrow 035](../background/tickets/035-narrow-one-direction-three-variants-one-winner.md) and recorded in
**ADR-0007**; the UI stack in **ADR-0008**; the light theme as a second token set in **ADR-0017**. Near-black indigo ground, elevated 6px-radius
panels, periwinkle accent, system-ui + ui-monospace, bar sparklines on a shared 30-day axis.

**`design/tokens.css` is the contract** — the single source of truth, inlined by
`build/serve.py` into every page at render time (`TOKENS_CSS`). Comps are reference-only.
Change a value there, not in a view. The fuller reasoning the ADRs were distilled from is
in `background/design/build-handoff.md` and `background/design/design-inputs.md`.

Root `DESIGN.md` is the **shipped** design system, re-derived from the built UI rather
than written ahead of it (ticket 052). It is an output; `tokens.css` is the input.

A *new* surface still runs the house design flow (prototype-first for a dense tool UI, then Wireframe → Diverge → Narrow → System) — the settled direction is an input to it, not a reason to skip it. **Artboard markup is never imported into `build/`** — artboards are comps, `tokens.css` is the contract.

Impeccable's hooks are live here: `PostToolUse` catches immediate-tier problems per edit, `Stop` runs the deep pass over every UI file touched in the session. `/impeccable hooks off` for greybox prototype tickets only.

## Build: this project

- Tracker is **GitHub Issues on this repo** (`dempseydata/hindsight`), default triage labels, single-context domain docs — recorded in `docs/agents/`. Issues are public; write them knowing that.
- Wayfinder discipline: one ticket per session, research excepted. Prototype liberally; a prototype's *answer* is captured (an ADR or a design input note), its code dies on a throwaway branch.
- **Evaluation** applies here — the what-pass is load-bearing model output. `eval/what_cases.json` + `eval/what_run.py` is the standing regression set (ticket 067); run it before any prompt or model-pin change, and the threshold is decided before the edit, never after.
- `security-preflight` before any push that changes what the public sees in `eval/`, `docs/screenshots/` or `background/`.
