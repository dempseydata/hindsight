# #31 Delta pass: greyboxes re-judged on the real backend

state: closed · labels: wayfinder:prototype · opened: 2026-08-18 · closed: 2026-08-19

Part of #30

## Question

The three greybox verdicts were judged on pre-build data: the where-view on ccwhere's `~/.ccwhere/ccwhere.db`, the why-view with simulated churn timing, the what-view assuming per-project audit files. The backend now exists and materially moved the ground. Regenerate the affected views against hindsight's real SQLite (run a fresh analysis run first if `local-data` is stale) and re-judge **only the deltas**:

- Hook panel on real `hindsight.hook` rows — the honest `duration_ms` (instrument-only) vs `cpu_ms` (per-firing cost) semantics of ADR-0005; the greybox only had a placeholder.
- Real snapshots, blobs and deterministically-linked change events replacing the hash-spread simulated churn (#6's noise policy re-checked on real timing).
- One cross-project audit table (ADR-0004) — the "project chip on every row" rider is now storage reality, not tension; does the ledger read as the cross-project surface it implied?
- Coverage-window honesty on every OTEL-fed panel — state when continuous capture began, never render a gap as zero.
- Sunk-cost registry keyed by install path (the double-count fix, now real) and self-exclusion of hindsight's own analysis sessions.

Which verdicts survive? A layout that dies on real data spawns a fresh prototype ticket. Throwaway branch `prototype/design-delta-pass`; master keeps only the verdict. Impeccable hooks off.



---

**comment · 2026-08-18**

Delta pass built — awaiting review (HITL: the re-judgement verdicts are yours).

**Generator:** `build/prototype-delta-pass.py` on throwaway branch `prototype/design-delta-pass` (throwaway branch in the private working repo — not exported). Run `python3 build/prototype-delta-pass.py`, then open `local-data/prototypes/delta-{what,why,where}.html` (bottom bar switches views; screenshots alongside). Winning variants only — what: ledger B · why: day-ledger C · where: panel dashboard A — all fed from `local-data/hindsight.db` (fresh: last analysis run 2026-08-18 13:57 UTC, so no re-run). Impeccable hooks are off.

**Delta-by-delta, with my read — react to each:**

**D1 — hook panel on real `hindsight.hook` rows.** 543 firings across the recommended three events (UserPromptSubmit 214 · Stop 192 · SessionStart 137). ADR-0005 semantics render cleanly: cpu_ms carries the table (p50 74–81ms, p95 87–107ms), duration_ms is a dim diagnostic column (~1ms), wall-cost-not-captured stated in the panel note. Coverage began 2026-08-17, so the 30-day sparks are two thin marks — honest, not broken. *My read: the reserved-panel decision pays off; placeholder retires.*

**D2 — real backstop replacing simulated churn.** Reality: baseline 2026-08-17T23:10, 5 runs since, **0 change events**, 5 blobs. Everything pre-baseline is silent by design, so the mechanical/churn lanes are empty and the day ledger runs findings-only — it survives that emptiness fine. *But the #6 noise policy is NOT re-judged here: there is no real churn timing yet to judge it on. My read: layout verdict survives; the noise policy stays provisionally settled, revisit in the styled build once change events accrue.*

**D3 — one cross-project audit table.** The ledger reads naturally as the cross-project surface the project-chip rider implied: 154 entries · 12 projects in one stream, chip on every row, chips filter instead of switch. ADR counts are the mechanical `adr_count` column. Two real-data warts: **29 audit rows are model-refusal text stored as markdown** (build bug — surfaced in a red collapsed row, needs a pipeline ticket), and scratch-dir project names make unreadable chips (chip policy, already under review).

**D4 — coverage honesty.** Two different windows, both stated as banners: transcript-derived panels have usage for **83 of 240** synced sessions (2026-07-11 → 08-17; older transcripts pruned before the substrate scan — unknown, not zero), OTEL/hook from 08-16/17. Note the where-view's history is ~37 days, far shorter than ccwhere's db the greybox was judged on.

**D5 — sunk-cost registry + self-exclusion.** The real `sunk_cost` table carries the drill: user-scope block first, per-project rows with plugin grouping (eager stub vs catalog), measured medians from first-usage-row-per-session (hindsight 56.4k over 44 sessions), double-count fixed. 793 self-excluded sessions stated in the header.

**The one verdict genuinely at risk — substrate gap.** ccwhere's parse gave the greybox skill/CLI consumer grain, per-call error flags, and message-lens tokens. `tool_events` has none of those, so the consumer league (dual lens), errors/day sparks, and the CLI panel **cannot be rebuilt** — the delta pages substitute a built-in-tools table + MCP servers panel. The dashboard hangs together, but the where-view resolution validated exactly those panels. Your call: (a) league grain becomes a build requirement (Bash-command parse, skill-name capture, error flags, message linkage in the substrate), or (b) the where-view ships thinner. Also spotted: one malformed tool name (`ls output/…` stored as a tool_events name) — parse wart.

**Bonus real-data observation for the Design bundle:** the 88-finding day (2026-08-02) is dominated by same-session near-duplicate findings (one convention restated as ~4 cards) — extraction redundancy visible at volume; a why-pass/ADR-0002 question, not a layout one.



---

**comment · 2026-08-19**

## Resolution

**All three greybox verdicts survive on the real backend. No layouts reopened.** Reviewed delta-by-delta with the operator; rulings:

- **D1 — hook panel: survives, placeholder retired.** Real `hindsight.hook` rows (543 firings, three recommended events) render the ADR-0005 semantics cleanly — `cpu_ms` carries the table (p50 74–81ms, p95 87–107ms), `duration_ms` is a dim diagnostic, wall-cost-not-captured stated. Two-day coverage reads honest, not broken.
- **D2 — day ledger survives the real backstop's honest emptiness** (baseline 2026-08-17, **0 change events**, findings-only rows). The #6 noise policy is **provisionally settled, not re-confirmed** — no real churn timing exists yet to judge it on. *Rider to the Design bundle: re-check the noise policy in the styled build once change events accrue.*
- **D3 — cross-project ledger confirmed.** One audit table renders as the cross-project surface the project-chip rider implied (154 entries · 12 projects · chip per row, chips filter, mechanical `adr_count`). Warts dispatched: refusal-text audit rows → build defect [#38](038-backfill-stored-model-refusal-text-as-audit-entries-29-rows.md) (out of this map's scope); scratch-dir chip naming → folded into the shared-chrome chip-policy rider.
- **D4 — coverage honesty confirmed in content; form goes to Design.** Usage covers 83 of 240 sessions (2026-07-11→08-17; pruned transcripts read unknown, not zero); OTEL from 08-16, hooks 08-17; 793 self-excluded sessions stated. *Rider: whether gaps render as banner prose or in-chart treatment (e.g. shaded axis regions) is a styled-build decision.*
- **D5 — sunk cost survives on the real registry.** Install-path keying kills the double-count (hindsight 78 enabled skills, not 188); plugin grouping and eager-stub/catalog split carry over; measured medians (first-usage-row-per-session) render as authority. The greybox's folder-tree framing (nested tiers, dormant badges) is a render-layer option rebuildable from `path`, not a requirement.
- **Substrate fork — decided: the consumer-league grain becomes a build requirement.** `tool_events` lacks skill/CLI consumer grain, per-call error flags, and message-lens token linkage, so the validated league (dual lens), errors/day sparks, and CLI panel could not be rebuilt. All four grains are transcript-derived and backfillable over the retained window; a richer substrate scan goes into the Build handoff. (Includes fixing the malformed-tool-name parse wart noted in #38.)

**Bonus observation to the Design bundle:** the 88-finding day (2026-08-02) is dominated by same-session near-duplicate findings — extraction redundancy visible at real volume; a why-pass/ADR-0002 question for the Build effort, not a layout question.

**Primary source:** `build/prototype-delta-pass.py` on throwaway branch `prototype/design-delta-pass` (throwaway branch in the private working repo — not exported); master keeps only this verdict. Data: `local-data/hindsight.db`, last analysis run 2026-08-18 13:57 UTC.


