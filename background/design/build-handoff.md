# Build handoff — what grill-with-docs consumes

The design effort ([map #30](../tickets/030-map-hindsight-design-validated-greyboxes-to-a-chosen-directi.md)) is
closed. This is the bundle for the top of the styled Build effort: `grill-with-docs`
interrogates the definition *and* these decisions, and writes the ADRs — done by
ticket #41: ADR-0007 (direction) and ADR-0008 (UI stack) now carry this reasoning;
what follows is the fuller source they were distilled from.

The bundle is three files plus this index:

1. **[tokens.css](../../design/tokens.css)** — the direction contract as code. Single source of
   truth; the server inlines it into every page at render time. Comps are
   reference-only.
2. **[design-inputs.md](design-inputs.md)** — everything the styled views must honour:
   scope (two views — what and where, per [#39](../tickets/039-scope-drop-the-why-view-from-v1.md)),
   shared header chrome, the spark system, per-view specifics, honesty rules, the
   judgement calls left open, and the build requirements riding alongside.
3. **This file** — the direction and UI-stack reasoning that lives nowhere else in the
   repo (it was decided in issue resolutions).

## Direction: V3 · Indigo deck

Chosen comparatively ([Diverge #34](../tickets/034-diverge-five-candidate-directions.md) →
[Narrow #35](../tickets/035-narrow-one-direction-three-variants-one-winner.md)), five candidates then
three variants, identical real content in every comp. Reference artboard:
`VariantIndigo.dc.html` on the ["Hindsight Narrow" canvas](https://claude.ai/code/artifact/74ca01e8-d31e-42e3-aa04-01d0efe0cc39).

- **Family:** observability workhorse (Grafana/Honeycomb lineage) — titled panels, stat
  tiles, shared 30-day axis, blue/red thresholds — with one graft from the
  terminal-instrument family: **bar sparklines**, not heat strips.
- **Look:** near-black indigo ground, elevated 6px-radius panels, periwinkle accent,
  28px stat numerals, system-ui + ui-monospace, 200ms ease hover lift.
- **Spark grammar (standard):** per-day bars on the shared 30-calendar-day axis, own
  peak per spark, missing day = gap, never zero.
- **Assets:** judged, none needed — no imagery surface exists in this direction.
- Full token values: [tokens.css](../../design/tokens.css). All values verified verbatim against the
  winning artboard.

## UI stack (from [#36](../tickets/036-decide-the-ui-stack.md), ADR-ready)

1. **On-demand foreground local server** — stdlib `http.server`, started to look,
   stopped when done; reads SQLite live; strictly read-only (never invokes the model,
   never writes the DB). This is ADR-0001's "on-demand foreground dashboard" — a
   foreground command, not a second daemon. Static regeneration is retired.
2. **Zero-dep vanilla UI** — Python-assembled HTML, one inline stylesheet, vanilla JS,
   sparks as inline SVG. No npm, no build step, no CDN fetches. Exceptions require an
   ADR.
3. **Tokens are code, comps are reference** — `tokens.css` committed and inlined;
   artboard markup never imported; page structure comes from the greybox-validated
   layouts.
4. **Two refresh controls, kept separate** — where-view metrics refresh is browser
   reload (live reads, no button, no polling); analysis runs via CLI plus a nightly
   launchd calendar job (a scheduled *invocation* of the on-demand app, not a
   background process — no nightly existed before; only the ingest listener is
   scheduled today). The server never grows a run button.

## Carry-alongs for grill-with-docs

- The **why-view drop ADR** ([#39](../tickets/039-scope-drop-the-why-view-from-v1.md)) +
  CONTEXT.md's "three views" framing update; why-pass removal from `analyze.py` is a
  Build ticket.
- A one-line clarifying note on ADR-0001's "schedules nothing" sentence (scheduled
  invocation ≠ background process).
- The **nightly launchd plist** as a small build ticket.
- The **richer substrate scan** ([#31](../tickets/031-delta-pass-greyboxes-re-judged-on-the-real-backend.md)):
  skill/CLI consumer grain, per-call error flags, message-lens token linkage.
- The judgement calls in design-inputs.md's "Left to the styled build" — judge against
  real data, don't re-litigate.
- Impeccable hooks are **back on** as of this handoff; the floor audit
  (`/impeccable audit`) belongs to the Build effort.
