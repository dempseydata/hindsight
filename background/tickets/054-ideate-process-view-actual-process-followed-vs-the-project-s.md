# #54 Ideate: process view — actual process followed vs the project's stated my-process.md

state: closed · labels: needs-triage · opened: 2026-08-26 · closed: 2026-08-29

A possible new view: capture the process actually followed in a project (from session history), and where the project has a stated process (`.claude/my-process.md`), compare actual against stated.

Scope questions before any design:
- Review existing projects to determine whether this applies to all projects or only a select few (how many even have a my-process.md or equivalent?).
- If no projects are configured for it, should the view hide entirely from the web UI (no nav entry)?
- What does "the process actually followed" mean operationally — skill invocations, phase-folder activity, ticket flow, commit cadence?

This is an ideation item, not a build ticket: the front door is `/mattpocock-skills:grill-me` (feature-scale ideation — not BMAD, which is reserved for new-product premises), closing with `grill-with-docs` if the decision deserves an ADR, and it lands as its own effort (likely its own wayfinder map) if it survives.




---

**comment · 2026-08-26**

**Grilled and decided** (grill-with-docs session, 2026-08-26). Recorded in CONTEXT.md ("The how-view" section) and **ADR-0010 — The how-view: mechanical process trail, operator-declared stages, no verdicts**.

Feasibility (hindsight as test case): **confirmed, with one discovery** — user-typed slash commands leave no tool event (the skill is injected into the user message, no Skill tool call), so the deliberate-process signal lives only in transcripts: 196 `/wayfinder` invocations in this folder's JSONL vs 0 in `tool_events`. The `<command-name>` marker is verbatim in the JSONL — a new mechanical grain type, no model needed. With it, skill events, phase-folder writes and audit titles jointly reconstruct the real arc (framing Jul 30 → grilling burst Aug 1 → prototype Aug 3 → build Aug 16+ → design Aug 18–20 → review Aug 25).

The decisions:

1. **A third view, `how`** — the process actually followed, per workspace folder. Not the why-view resurrected: no rationale attribution, no model judgement.
2. **Mechanical assembly** — command grains + skill invocations + phase-folder writes in date order; audit titles supply the prose. No model narrative (would make model output load-bearing → full Evaluation discipline).
3. **Process declaration** — `my-process.md` gains frontmatter: ordered stages → observable markers, route resolved at authoring time (branching, incl. the two design routes, stays in prose). Checker limited to presence + first/last-seen + off-script list; **no order rules, no verdicts** — comparison is juxtaposition, deviation is informative, judgement is the operator's.
4. **Nothing hides** — no declaration ⇒ raw ungrouped trail, stated-process panel simply absent. The ticket's hide-if-unconfigured question dissolves.
5. **Stage-anchored output** — trail events bucketed under the project's own stage names so inter-stage back-and-forth is visible; rendering mechanics deferred to greybox prototyping.

Lands as **its own effort with its own wayfinder map** (not map #40). Ready for wayfinder charting.


---

**comment · 2026-08-29**

Superseded — this ideation shipped.

This item asked for a view comparing the process actually followed against a project's stated `my-process.md`. It was charted into map #58, which is now closed with its destination met: the styled `/how` view is live and serving.

Its three scope questions were all answered on the way through:

- **Does it apply to all projects or a few?** A few — three declare (`hindsight`, `project-template`, `thisisme`). ADR-0011 fixed the frontmatter schema; #62 authored the declarations.
- **Should it hide when no project is configured?** No — it degrades to the raw ungrouped trail rather than vanishing (ADR-0010).
- **What does "the process actually followed" mean operationally?** Skill invocations, user-typed slash commands (the command grain, #61) and first-touch writes under the project root, stage-bucketed by the declaration with a longest-prefix path match, off-script events listed rather than hidden.

Closing as delivered rather than abandoned.

