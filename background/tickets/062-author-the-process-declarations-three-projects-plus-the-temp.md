# #62 Author the process declarations: three projects plus the template

state: closed · labels: wayfinder:task · opened: 2026-08-26 · closed: 2026-08-27

## Question

With the declaration schema settled, author the frontmatter with the operator: the three live projects' `my-process.md` files plus `project-template/` (per ADR-0010's consequences). Each project declares only its own resolved route — branching stays in the house-pipeline prose.

HITL: the declarations are the operator's own statements of their process; the agent drafts from each project's existing prose and observed history, the operator corrects and approves.

Resolution records which files landed where, and any schema friction discovered while authoring (feed it back to the schema ADR if the shape has to move).



---

**comment · 2026-08-27**

## Draft declarations — awaiting operator approval (HITL)

Frontmatter written (uncommitted) at line 1 of four files. Each was drafted from the project's own prose and its observed command history in `local-data/hindsight.db`; all four pass a throwaway ADR-0011 strict-subset check (fence at line 1, `stages:` only, unique names, no marker in two stages).

| Project | Stages | Departures from the ADR-0011 worked example |
| --- | --- | --- |
| `hindsight/.claude/my-process.md` | Ideate · Design · Plan · Build | Worked example verbatim, plus `setup-matt-pocock-skills` (Plan), `ponytail-audit` + `graphify` (Build) — all in its prose, `setup-matt-pocock-skills` observed once in thisisme's history |
| `thisisme/.claude/my-process.md` | Ideate · Design · Plan · Build | Domain docs live under `build/` there, so Plan paths are `build/docs/adr/` + `build/CONTEXT.md`; Build paths are the Next.js source dirs `build/app/`, `build/components/`, `build/lib/` rather than `build/` (see friction 2); `PRODUCT.md` in Ideate; `security-preflight` in Build (it deploys) |
| `Ontology-for-AI/.claude/my-process.md` | Ideate · Plan · Build | **No Design stage** — exploration with no visual surface, per its prose's "skip Design entirely" rule; its older chain has `grill-with-docs` as front door, `wayfinder` only when too big — same Plan bucket, order reflects that. Note the repo has never had a commit; every file is untracked |
| `project-template/.claude/my-process.md` | Ideate · Design · Plan · Build | The house default route in full (hindsight's block + `security-preflight`). A project copying the template prunes what it doesn't run — e.g. drops Design for a no-surface product |

**Judgement calls to confirm or overrule:**
- Ontology-for-AI without a Design stage.
- `design-sync` sits in Design everywhere; thisisme's prose says it is reverse-only (repo → canvas, post-build). Move it to Build for thisisme if you regard it as build tooling.
- Housekeeping commands (`/clear` ×48, `/compact`, `/model`) are deliberately undeclared — they are not process. They will show in off-script unless the view filters them; that is a presentation call for #63/#64, not a declaration.

**Schema friction found (ADR-0011 shape does not need to move, but #63's matcher must handle both):**
1. **Leading slash.** `command_grains.command` is verbatim `<command-name>` text and carries the `/`: `/mattpocock-skills:wayfinder`, `/design-sync`. ADR-0011's tail-segment rule matches the first (tail after last colon = `wayfinder`) but not the second (no colon, `design-sync` ≠ `/design-sync`). The matcher must strip the leading `/` from stored grains before comparing; declarations stay slash-free.
2. **Overlapping path subtrees.** ADR-0011 rejects the *same* marker in two stages but says nothing about nested subtrees (`build/` in Build, `build/docs/adr/` in Plan). Either longest-prefix wins or overlap is invalid — the ADR should say which. thisisme's draft dodges it by declaring the source dirs instead of `build/`; if longest-prefix is adopted, `build/` is the more honest Build marker.
3. Skill markers remain inert until the Skill tool's `skill` argument is extracted (ADR-0011 already notes this; `tool_events` has 65 hindsight `Skill` rows with no skill name).

Say which drafts to correct; on approval I'll commit the four files (each in its own repo) and close this with the file list.



---

**comment · 2026-08-27**

## Resolution

Operator approved the drafts with two amendments; landed and committed:

- `hindsight/.claude/my-process.md` — c2f06dc
- `thisisme/.claude/my-process.md` — 6311e0e (Plan paths under `build/`; Build paths are the Next.js source dirs)
- `project-template/.claude/my-process.md` — 144537c (house default route; prune on copy)
- **Ontology-for-AI declares nothing.** Operator's call: it is a learning project and should never have had a process file. `.claude/my-process.md` and the `@` include in its CLAUDE.md were removed (repo has no commits; untracked either way). "Three projects plus the template" is two.

Amendment 2: a **Release** stage — `security-preflight`, `graphify`, `document-app` — appended to all three declarations. The prose does not yet describe it; ADR-0011 permits a stage declared ahead of its tooling/prose, and the operator intends a process-doc revisit (cleanup, retire old-skill references, write up Release) as a separate effort outside this map.

Schema friction, fed to #63 and to be recorded in ADR-0011: stored grains carry the leading `/` verbatim (strip before tail-segment matching); nested path subtrees across stages need a longest-prefix-wins or invalidity rule. Skill markers stay inert until the Skill tool's `skill` argument is extracted. Housekeeping commands (`/clear`, `/compact`, `/model`) deliberately undeclared — filtering them is a presentation call for the view tickets.

