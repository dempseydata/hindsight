# #12 Greybox the where-view

state: closed · labels: wayfinder:prototype · opened: 2026-08-01 · closed: 2026-08-03

## Question

Layout the token/cache/latency/MCP panels on real parsed data (ccwhere's existing `~/.ccwhere/ccwhere.db` is a legitimate data source for the greybox). Deliberately last: blocked behind both wedge prototypes. Sharpens the parity-vs-trim fog. Impeccable hooks off.

Part of #1



---

**comment · 2026-08-03**

## Resolution

**Winner: variant A — the panel dashboard.** Tiles → consumer league → models + latency → MCP servers → CLI tools → session-start sunk cost with composition drill → hook-activity placeholder. B (day ledger) and C (consumer league as spine) die with the branch; C's per-consumer drill and sparks were grafted into A during review.

**Shared header chrome, extended** (rider to the Design-inputs bundle): project chips + stacked per-day token chart + click-a-bar time filtering (as validated by the sibling greyboxes), **plus window presets** — last 7/14/28/90/all, **default last 14** — anchored to the last-synced day, with a chart click overriding the preset. A "hide cache reads" toggle answers cache-read dominance (8.6B vs ~356M everything-else): the chart is unreadable without it.

**Sparklines are a system, not a decoration**: every spark (league, models, sunk-cost, MCP tools, CLI tools) shares one 30-calendar-day axis ending at the last-synced day, newest rightmost, empty days as gaps — so relative usage patterns scan across panels column-for-column. CLI tools with errors carry a second errors/day spark directly beneath the calls spark (own peak, same axis) — on real data it immediately separated recent/high-usage-correlated errors from isolated one-offs.

**Panel decisions (parity vs trim):**
- **Consumer league**: dual-lens kept (session-lens + message-lens), spark column, click-to-expand per-consumer detail (active days, first/last used, p50/p95/max, errors, MCP tool split, per-project calls).
- **MCP servers**: server → tool table with per-tool aligned sparks.
- **CLI tools**: new panel mirroring MCP (the parse has no subcommand grain, so the drill is spark + latency + projects); <5-call consumers lump into one collapsed row — render policy to be judged in the styled build.
- **Sunk-cost ledger**: medians table (workspace projects first, scratch/system dirs after) + **the composition drill that ccwhere never quite landed** — ccwhere's `context_tree` scan reused wholesale, rendered as a nested folder tree with +eager / =accumulated / measured-median-as-authority per node, itemized on expand (CLAUDE.md chain, skills/commands stubs vs catalog, per-folder plugins), **plugins as a grouping level** with per-plugin subtotals, and dormant subfolders shown. Nested-subfolder CLAUDE.md tiers (incremental loading) are modeled directly. This presentation works; it carries to the styled build.
- **Pricing/cost columns: trimmed.** Never rendered; ADR-0003's bring-your-own-auth makes them non-load-bearing. ccwhere's hours/events drill-down also not rebuilt.
- **Hook activity: KEPT** as a reserved panel. No OTEL source exists (falsified, #2) — self-instrumentation (a hook POSTing to the ingest listener) goes into the build handoff.

**Bug found in ccwhere by the drill** (rebuild must fix): `installed_plugins.json` holds one record per project install, often same installPath — `_plugin_descs` scans the path once per record, doubling skill counts (188 shown vs 94 real at hindsight). Registry must key by installPath. Greybox carries a marked monkey-patch. Enablement filtering itself (settings.json + settings.local.json `enabledPlugins`, per folder) was verified correct.

**Honesty notes for Design**: sessions attribute to their first day under a time window (zeros session-lens counts on short windows — marked in UI); chip policy (chips only for projects ≥1% of tokens, 16 tail projects chipless) is itself under review; sunk-cost scan reads today's filesystem while medians are measured; the itemized-eager vs measured-median gap is system-prompt/built-in overhead, flagged as file-invisible.

**Primary source:** the prototype (all three variants + five review iterations) lives on the throwaway branch `prototype/where-view-greybox` (throwaway branch in the private working repo — not exported) (`build/prototype-where-view.py`); master keeps only this verdict. Data was ccwhere's `~/.ccwhere/ccwhere.db` (453 sessions, 19.4k tool calls, synced through 2026-07-19).


