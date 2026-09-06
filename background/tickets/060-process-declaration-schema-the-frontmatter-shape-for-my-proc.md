# #60 Process-declaration schema: the frontmatter shape for my-process.md

state: closed · labels: wayfinder:grilling · opened: 2026-08-26 · closed: 2026-08-27

## Question

The exact machine-readable frontmatter for `my-process.md` — the process declaration of ADR-0010. To settle, with the operator:

- How stages are listed and named (ordered list; whose names — the operator's own vocabulary?).
- The marker vocabulary: typed commands, skill invocations, phase-folder writes — and how each is expressed (exact names? prefixes/globs? plugin-qualified skill names?), such that each marker maps mechanically to an observable already in (or landing in) the DB: command grains, Skill tool events, file-write paths.
- File placement and parsing rules: YAML frontmatter atop the existing prose, what the parser tolerates, what makes a declaration invalid (and what the view does then — presumably degrade, per the juxtaposition rule).
- The minimal syntax that keeps the prose below the frontmatter the authority on meaning — the schema carries mapping, never semantics, and no condition language (out of scope per ADR-0010).

Constraints already decided (ADR-0010, not to reopen): branching resolves at authoring time — each project declares only its own route; no order rules; no verdicts.

Output: the schema decided and recorded — an ADR (or ADR-0010 addendum) plus CONTEXT.md vocabulary if new terms emerge.



---

**comment · 2026-08-27**

## Resolution

Schema decided with the operator (grilling session) and recorded as **ADR-0011** (`docs/adr/0011-process-declaration-schema.md`), plus CONTEXT.md vocabulary (process-declaration entry extended; new *declaration states* term).

The decisions, compressed:

- **Container**: `---`-fenced frontmatter at line 1 of `<project-root>/.claude/my-process.md` — the only location read. A strict, hand-parsed YAML subset (no yaml module exists in the stack; ADR-0008 forbids adding one): "valid" is defined by our parser, not the YAML spec. The convention is project-level and optional — the operator is retiring the user-level process file.
- **Grammar** (all of it): one top-level key `stages:` — an ordered list of maps, each with a required unique `name` plus optional `commands`/`skills`/`paths` lists of strings. No version key, no prose fields; prose below the fence stays the sole authority on meaning. List order is rendering-only.
- **Name matching** (commands/skills): bare names match the whole tail segment after the last colon (`grilling` matches `mattpocock-skills:grilling`, never `grilling-with-pellets`); qualified names match exactly. Case-sensitive, no substrings, no globs. Survives plugin re-namespacing; a real rename lands in off-script (the rot detector working).
- **Path matching**: relative to project root; trailing `/` = subtree, otherwise exact file.
- **Three states, nothing hides**: absent → raw trail, no panel, no error. Invalid → raw trail + visible one-liner naming reason and line. Valid → stage-anchored view.
- **Strictly invalid, no partial salvage**: unknown keys, non-list values, missing/duplicate stage names, and the same marker in more than one stage (ambiguity resolved at authoring, same posture as ADR-0010's branching). Empty marker lists and marker-less stages are valid ("nothing observed" is honest).
- **Worked example**: hindsight's four stages — Ideate, Design, **Plan**, Build. Plan is new: `wayfinder`/`grill-with-docs` open it, `to-spec`/`to-tickets` are its final pieces, `prototype` and `docs/adr/` + `CONTEXT.md` writes sit in it; Build starts at `implement`. Seeds ticket #62.

Downstream notes surfaced while grilling: `tool_events` stores `name='Skill'` with **no skill name** — skill-marker support needs that extraction, landing with #61 or #63. The grammar paragraph in ADR-0011 is #63's parser spec.


