# #33 Consolidate the Design-inputs bundle

state: closed · labels: wayfinder:task · opened: 2026-08-18 · closed: 2026-08-20

Part of #30

## Question

One note — `design/design-inputs.md` — consolidating everything the styled comps must honour, currently scattered across the greybox resolutions. Sources: resolutions of #5, #6, #12, #14, ADR-0004/0005, and the delta-pass verdict (which blocks this). Contents at minimum:

- Shared header chrome: project chips (≥1%-of-tokens policy still under review), stacked per-day chart, click-a-bar time filtering, window presets 7/14/28/90/all (default 14d), cache-read toggle.
- The spark system: one shared 30-calendar-day axis across all panels, newest rightmost, empty days as gaps; errors/day sparks beneath call sparks.
- Ledger patterns: what-view one row per session, why-view one row per day; expand for detail.
- Evidence anatomy: quotes collapsed behind "N quotes · status" summaries, exact/fuzzy/unresolved badges, unresolved rendered honestly; the why-line-near-duplicates-first-quote observation.
- Honesty notes: coverage window, sessions attribute to first day, file-invisible system-prompt overhead, measured-median-as-authority.
- Left for the styled build to judge: ADR-count badges, zero-decision sessions, chip policy, low-volume CLI lump.



---

**comment · 2026-08-20**

Scope change before this ticket runs: the why-view is dropped from v1 wholesale ([#39](039-scope-drop-the-why-view-from-v1.md) — see its resolution for what dies and what stays). When consolidating the bundle, prune every why-view input: the #6 greybox riders, the noise-policy re-check, evidence/quote anatomy, and the extraction-redundancy observation from #31. Survivors to keep: shared header chrome (chart + time filtering + project chips — validated via the why greybox but owned by the shared header), and everything what/where. The bundle should also carry the two-view destination so grill-with-docs writes the drop ADR at the top of Build.


---

**comment · 2026-08-20**

## Resolution

**Done — the bundle exists: [`design/design-inputs.md`](../design/design-inputs.md)** (commit 6c2540a on master).

Consolidated from the greybox resolutions (#5, #6, #12), the audit-format lock (#14 / ADR-0004), ADR-0005, and the delta-pass verdict (#31), pruned per the scope cut (#39):

- **Pruned as void:** every why-view input — the #6 riders, the noise-policy re-check, evidence/quote anatomy, the why-duplicates-quote observation, and the extraction-redundancy observation.
- **Kept:** shared header chrome in full (chips-filter-not-switch, stacked per-day chart, click-a-bar time filtering, 7/14/28/90/all presets defaulting 14d, cache-read toggle) — validated via the why greybox but shared-owned, so unaffected by the drop; the spark system (one 30-day axis, errors/day sparks beneath call sparks); the what-view ledger (row per session, project chip per row, mechanical ADR counts); the where-view panel dashboard delta-confirmed panel by panel; the honesty rules (coverage windows, first-day attribution, file-invisible overhead, measured-median-as-authority, silent hook failure).
- **Left to the styled build** (defined semantics, open presentation): ADR-count badge, zero-decision sessions, chip policy, the CLI lump row, coverage-gap form (banner vs in-chart).
- **Carried for grill-with-docs, not the comps:** the two-view destination + drop ADR (#39), the richer-substrate-scan build requirement, why-pass removal, defect #38.

The bundle is the design half of the Build handoff; its exact seam into grill-with-docs sharpens at the exit ticket, per the map's fog.

