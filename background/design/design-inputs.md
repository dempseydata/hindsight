# Design inputs — the bundle for the styled build

Everything the styled comps must honour, consolidated from the greybox resolutions
([what #5](../tickets/005-greybox-the-what-view-audit-log.md),
[why #6](../tickets/006-greybox-the-why-view-change-timeline.md),
[where #12](../tickets/012-greybox-the-where-view.md)),
the audit-format lock ([#14](../tickets/014-lock-the-audit-format.md) / ADR-0004),
the hook-instrumentation decision (ADR-0005), and the delta-pass verdict
([#31](../tickets/031-delta-pass-greyboxes-re-judged-on-the-real-backend.md)) — pruned for the v1 scope cut
([#39](../tickets/039-scope-drop-the-why-view-from-v1.md)). This is the design half of the
Build handoff; `grill-with-docs` consumes it at the top of the styled Build.

## Scope: v1 is two views

**What and where, plus shared header chrome.** The why-view was dropped from v1 wholesale
(#39): its surface, the why-pass pipeline, and the standing eval burden that existed almost
entirely for it. The silent-change backstop *capture* stays but renders nowhere in v1.
`grill-with-docs` writes the scope ADR at the top of Build and updates CONTEXT.md's
"three views" framing. All why-specific riders from the greyboxes (noise-policy re-check,
evidence/quote anatomy, the why-duplicates-quote observation, extraction redundancy) are
void and deliberately absent from this bundle.

## Shared header chrome (both views)

Validated across the greyboxes — much of it via the why greybox, but the chrome is
shared-owned, so it survives the why-view's drop unaffected (#39).

- **Project chips filter, never switch.** One cross-project stream per view; chips compose
  with time filters — active chips reshape the chart bars and hide non-matching rows.
- **Stacked per-day chart** between the chips and the content: calendar-continuous,
  scrollable, newest at right.
- **Click-a-bar time filtering:** one click selects a day, a second click a range, again
  deselects, clear resets.
- **Window presets:** last 7 / 14 / 28 / 90 / all, **default 14**, anchored to the
  last-synced day; a chart click overrides the preset.
- **"Hide cache reads" toggle** — the where-view chart is unreadable without it
  (8.6B cache-read tokens vs ~356M everything else at greybox time).
- Chip policy is still open — see *Left to the styled build*.

## The spark system

Sparklines are a system, not a decoration: **every spark shares one 30-calendar-day axis**
ending at the last-synced day, newest rightmost, empty days rendered as gaps — so relative
usage patterns scan across panels column-for-column. Tools with errors carry a second
**errors/day spark directly beneath the calls spark** (own peak, same axis); on real data
this immediately separated usage-correlated errors from isolated one-offs.

## What-view: the ledger

- **Presentation (greybox winner B):** one collapsed row per session —
  date · title · counts (n did · n decided · n ADR) — expanding to the full
  Did / Decided / Setup-changes entry. The whole month fits on ~2 screens.
- **Cross-project surface:** one audit table (ADR-0004), **project chip on every row**;
  per-project separation is a query, not a file layout. Confirmed on real data — 154
  entries across 12 projects read naturally as one stream (#31 D3).
- **Granularity:** one entry per session, flat; a day roll-up is render-time grouping only.
- **ADR count is mechanical** — "ADRs touched", derived from tool events, never
  model-extracted. Whether it renders as a badge is the styled build's call.

## Where-view: the panel dashboard

Greybox winner A (#12), confirmed on the real backend (#31):

- **Panel order:** tiles → consumer league → models + latency → MCP servers → CLI tools →
  session-start sunk cost with composition drill → hook activity.
- **Consumer league:** dual lens (session-lens + message-lens), spark column,
  click-to-expand per-consumer detail (active days, first/last used, p50/p95/max latency,
  errors, MCP tool split, per-project calls).
- **MCP servers:** server → tool table with per-tool aligned sparks.
- **CLI tools:** mirrors MCP (spark + latency + projects); consumers with <5 calls lump
  into one collapsed row — render policy is the styled build's.
- **Sunk-cost ledger:** user-scope block first, per-project rows with **plugin grouping**
  and per-plugin subtotals (eager stub vs catalog split); **measured medians**
  (first-usage-row-per-session) render as the authority figure. The greybox's nested
  folder-tree framing (tiers, dormant badges) is a render-layer option rebuildable from
  `path`, not a requirement (#31 D5). Self-excluded session count stated in the header.
- **Pricing/cost columns: never rendered** (ADR-0003 bring-your-own-auth makes them
  non-load-bearing).
- **Hook activity panel** (real; placeholder retired — #31 D1): `cpu_ms` carries the
  table (p50 74–81ms, p95 87–107ms at delta time); `duration_ms` is a dim diagnostic
  column; the panel states that true wall cost is not captured (ADR-0005).

## Honesty rules

These bind every OTEL-fed panel, both views:

- **Coverage windows stated, gaps never rendered as zero.** At delta time: usage for 83 of
  240 synced sessions (2026-07-11 → 08-17; pruned transcripts read *unknown*, not zero);
  OTEL from 08-16, hooks from 08-17.
- **Sessions attribute to their first day** under a time window — zeros session-lens
  counts on short windows; mark it in the UI.
- **Sunk-cost scan reads today's filesystem while medians are measured**; the
  itemized-eager vs measured-median gap is system-prompt/built-in overhead — flag it as
  file-invisible.
- **Hook failure is silent by design** — a dead listener means absent rows; coverage
  honesty is the compensating control (ADR-0005).

## Left to the styled build's judgement

Defined semantics, open presentation — judge against real data, don't re-litigate:

- ADR-count badge: does it earn its row space?
- Zero-decision sessions (~half of all sessions): how do they read?
- Chip policy: the ≥1%-of-tokens threshold, and scratch-dir names making unreadable chips.
- The low-volume CLI lump row.
- Coverage-gap form: banner prose vs in-chart treatment (e.g. shaded axis regions) (#31 D4).

## Build requirements riding alongside (for grill-with-docs, not the comps)

- **Richer substrate scan** (#31): `tool_events` lacks skill/CLI consumer grain, per-call
  error flags, and message-lens token linkage — the consumer league, errors/day sparks,
  and CLI panel depend on all three. Transcript-derived, backfillable over the retained
  window.
- **The why-view drop ADR** (#39) + CONTEXT.md's "three views" framing update.
- Why-pass removal from `analyze.py` and the schema — Build-effort ticket, not design.
- Defect [#38](../tickets/038-backfill-stored-model-refusal-text-as-audit-entries-29-rows.md) (refusal-text audit
  rows; malformed tool-name parse wart) — already ticketed.

## Real data and the floor

Comps carry real content from `local-data/hindsight.db` — never lorem ipsum. The
mechanical floor rules in my-process's Design section bind every comp (named tokens,
semantic roles with AA `-text` weights, red pairs with blue, accent limits, chart data
ink on its own palette, line-height ≥ 1.50 long-form, no runtime font fetches); they are
not restated here.
