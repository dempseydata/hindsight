# ADR-0011: Process-declaration schema — strict YAML subset, tail-segment matching, loud invalidity

**Date:** 2026-08-26 · **Status:** accepted · **Decides:** issue #60

## Context

ADR-0010 decided *that* `my-process.md` gains machine-readable frontmatter — the process declaration mapping the operator's own stages to observable markers. This ADR decides the schema itself. Two facts constrain it: the stack has no YAML parser and ADR-0008's zero-dep rule forbids adding one, so the format must be hand-parseable by a small stdlib parser; and `my-process.md` is `@`-included into every session's context, so every frontmatter line is a token tax on every future session of a declaring project. The convention is **project-level and optional** — the operator is retiring the user-level process file; a project without the file simply has no declaration.

## Decision

**Container.** A `---`-fenced frontmatter block starting at line 1 of `<project-root>/.claude/my-process.md` — the only location the trail assembly reads, no fallbacks. The format is a strict, documented YAML subset: "valid" is defined by our parser, not the YAML spec. No anchors, no multiline scalars, no flow-style beyond inline `[a, b]` lists.

**Grammar** (the whole of it): one top-level key `stages:`, holding an ordered list of maps. Each stage map has a required, unique `name` (free text, the operator's own vocabulary) and optional `commands`, `skills`, and `paths` lists of strings — the three marker types, mirroring ADR-0010's three observables (command grains, Skill tool events, file-write paths). Nothing else: no `version` key (a future shape change fails the strict parser visibly and the handful of declaring files migrate by hand), no per-stage prose or description fields — the prose below the fence remains the sole authority on meaning. List order is the stated order, used only for rendering the stated-process panel; the checker never enforces it.

**Name matching** (`commands` and `skills` — the same names seen through two capture paths): a marker containing no colon matches a stored name that equals it, or whose entire segment after the last colon equals it (`grilling` matches `grilling` and `mattpocock-skills:grilling`, never `grilling-with-pellets`); a qualified marker matches exactly. Whole-segment equality only — no substrings, no globs, case-sensitive. Bare names survive plugin re-namespacing (packaging noise, not process change); a genuine skill rename still lands in off-script, which is the rot detector working. Two plugins colliding on a tail name is resolved by writing the qualified form.

**Path matching:** relative to the project root, case-sensitive. A trailing `/` matches any write under that subtree; no slash matches exactly that file.

**Three declaration states, nothing hides:**

1. *Absent* — no file, or no fence at line 1: raw ungrouped trail, no stated-process panel, no error.
2. *Invalid* — fence present but content fails the subset: raw ungrouped trail **plus a visible one-liner naming the reason and line**. A fence written wrong must never be indistinguishable from a fence never written.
3. *Valid* — the full stage-anchored view.

**Strictly invalid**, whole declaration rejected with no partial salvage: unknown keys at any level, a non-list where a list is expected, a stage without a `name`, duplicate stage names, and **the same marker declared in more than one stage** — bucketing ambiguity is rejected at parse time and resolved at authoring, the same posture ADR-0010 takes for branching. Strictness is the typo detector: a silently ignored misspelled key would drain a stage's markers into off-script and misrepresent the process. Deliberately *not* invalid: empty marker lists and marker-less stages — such a stage renders "nothing observed", which is honest and lets a stage be declared before any tooling for it exists.

## Worked example — hindsight's own declaration (seeds ticket #62)

```yaml
---
stages:
  - name: Ideate
    commands: [bmad-brainstorming, discover, red-team-prd, pre-mortem, grill-me]
    paths: [ideation/, definition/]
  - name: Design
    commands: [design-sync, impeccable]
    paths: [design/]
  - name: Plan
    commands: [wayfinder, grill-with-docs, to-spec, to-tickets]
    skills: [grilling, domain-modeling, research, prototype]
    paths: [docs/adr/, CONTEXT.md]
  - name: Build
    commands: [implement, code-review, ponytail-review, diagnosing-bugs]
    skills: [tdd, code-review]
    paths: [build/]
---
```

Authoring decisions it records: Evaluation is absent because `my-process.md` insists it is a recurring discipline, not a stage. **Plan** is a distinct stage — `wayfinder` and `grill-with-docs` open it, `to-spec` and `to-tickets` are its final pieces, and Build starts where code starts, at `implement`. `prototype` sits in Plan (encountered mid-wayfinding under the prototype-first path), resolving its Design/Build ambiguity at authoring time. `docs/adr/` and `CONTEXT.md` follow `grill-with-docs` and `domain-modeling` into Plan as planning artifacts. Plan sits between Design and Build in the stated order, matching how the prose reads; hindsight actually planned before designing, and that interleaving showing against the stated order is the texture the view exists to display, not something the declaration papers over.

## Considered options

- **Full YAML via a vendored parser** — flexibility nobody asked for, at the cost of the zero-dep rule's spirit and an unboundable definition of "valid".
- **A custom line format** — cheaper still to parse, but idiosyncratic; fenced frontmatter keeps the file legible as ordinary Markdown to every editor and tool.
- **Map keyed by stage name instead of a list** — terser, but silent duplicate-key loss, awkward names, and ordering by convention rather than by an actual list.
- **Prefix or glob matching for names** — substring creep (`grilling` swallowing `grilling-with-pellets`); whole-segment equality keeps matching mechanical and predictable.
- **Tolerating duplicate markers across stages** (first-wins or double-bucket) — either a silent precedence rule or double-counting; both are the checker growing judgement ADR-0010 swore off.
- **A `version` key** — speculative; the strict parser already makes a shape change loud.

## Consequences

- Ticket #63 (trail assembly + dumb checker) hand-rolls the subset parser and the three-state degradation; the grammar above is its spec.
- Ticket #62 copies the worked example into hindsight's real `my-process.md`, then authors the other declaring projects and the template.
- Skill markers depend on the Skill tool's `skill` argument being extracted — today `tool_events` stores `name='Skill'` with no skill name; the extraction lands with the command grain (#61) or trail assembly (#63).
- The operator retires the user-level process file separately; the declaration is a per-project opt-in and absence is a designed state, not an error.

## Amendments (ticket #63, 2026-08-27)

Settled while building the pipeline; the grammar above stands.

- **One name pool.** `commands` and `skills` are the same names seen through two capture paths — `/implement` typed is a command grain, `Skill(implement)` is a tool event — so a name marker in either list matches an event of either kind. The duplicate-marker rule therefore spans both lists across stages, and is checked with the matching rule itself: bare `grilling` in one stage and `x:grilling` in another collide (the qualified escape hatch only resolves a collision when *both* sides are qualified). The same name in one stage's `commands` and `skills` is not ambiguous and stays valid.
- **Leading slash.** Stored grains carry the typed `/` verbatim; it is stripped before matching. Markers are written without it.
- **Nested path subtrees** (`build/` in one stage, `build/docs/` in another) are distinct markers, not duplicates: the longest matching prefix wins. Mechanical, and the only reading under which a subtree can be carved out of a parent.
- **Skill markers are live.** The Skill tool's `skill` argument has been stored as `tool_events.consumer` since #42; the "inert until extracted" consequence above is stale.
- **Also invalid:** a marker key given twice in one stage (the second list would silently replace the first), and `#` comment lines inside the fence (the grammar allows nothing else). Every invalidity names its line.

## Amendment (ticket #65, 2026-08-29)

- **A marker that opens every session marks nothing.** `wayfinder` is removed from hindsight's Plan markers (the worked example above is historical): it opens every ticket session, so as a marker it coloured Build sessions Plan for their first event. Plan is now evidenced by `grill-with-docs`, `to-spec`, `to-tickets`, the planning skills and the planning paths. The same holds for `/clear` — both are session boundaries, not process steps, and they dominate the off-script list; whether the declaration grows an ignore list or the view drops them is a separate ticket. thisisme and project-template still list `wayfinder` and want the same edit.

## Amendment (ticket #70, 2026-08-28)

- **No `ignore:` key.** Session boundaries — Claude Code's own `/clear` and `/model`, and `wayfinder` as the house pipeline's session front door — are set aside by the view, not declared per project. The fact that a command opens a session rather than marks a step is a platform or house convention, not a project's process; declaring it in every `my-process.md` would repeat it four times and bury the list again in any project that forgot. The set is fixed in `build/how.py` (`SESSION_BOUNDARIES`), matched by the same name rule as markers, and applied **only to events no stage claimed** — a declaration that lists `wayfinder` under a stage still wins, so declared beats dropped. Nothing is hidden: the off-script total states the count and per-name breakdown of what was set aside (hindsight on 2026-08-28: 138 → 50 off-script events, 88 excluded). Extend the set only when a new opener is observed dominating the list, never speculatively.
