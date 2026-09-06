# #48 Where-view: the styled panel dashboard

state: closed · labels: wayfinder:task · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Build the styled where-view on the server + chrome, panel order per design-inputs.md: tiles → consumer league (dual lens, spark column, click-to-expand detail) → models + latency → MCP servers (server → tool table, aligned sparks) → CLI tools (consumers with fewer than 5 calls lumped into one collapsed row) → sunk-cost ledger (user-scope first, plugin grouping + subtotals, measured medians as the authority figure, self-excluded count in header) → hook activity (`cpu_ms` carries the table, `duration_ms` dim, wall-cost-not-captured stated).

Spark system throughout: shared 30-calendar-day axis, own peak per spark, missing day = gap, errors/day spark directly beneath the calls spark. Honesty rules bind every panel. Pricing/cost columns never rendered.

Judge against real data and record: the low-volume CLI lump row's rendering, and coverage-gap form (banner prose vs shaded axis regions).



---

**comment · 2026-08-25**

## Resolution

**Live at `/where` on the on-demand server, browser-verified against the real database** (250 sessions, ~14.4k tool calls), with the shared chrome — chips, presets, click-a-bar, hide-cache-reads — reshaping every panel client-side. Panel order exactly as specified: tiles → consumer league → models + latency → MCP servers → CLI tools → sunk-cost ledger → hook activity. All 14 serve tests pass; zero console errors. Commit b5c2a2c.

**The two calls the ticket asked judged and recorded:**

- **Low-volume CLI lump row:** one collapsed `<details>` row beneath the table — "N programs under 5 all-time calls · M calls in window (one-offs and Bash-parse leakage — known scan ceiling)" — expanding to a name ×count list. Membership judged on **all-time** calls so the row is stable across window changes; the #42 parse-ceiling junk (`let`, JS keywords) lands here, and junk that clears 5 all-time (`const` ×14) renders honestly as what the scan classified. Default 14-day window: 6 lumped programs, 9 calls.
- **Coverage-gap form: shaded axis regions won, hybridised.** OTEL-fed sparks (hook panel) draw a dim `--o-gapline` band across pre-coverage days — the 30-day axis is two-thirds pre-coverage for hooks, and shading reads as "not captured" in-chart where banner prose has to be remembered. Prose survives as exactly one global coverage line atop the view (usage 93/250 · OTEL from 08-16 · hooks from 08-17 · 802 self-excluded) plus one short honesty note per panel. No banner walls.

**Further presentation judgements decided against real data:**

- **League membership:** 217 distinct consumers exist; rows need ≥5 all-time calls (54 qualify), ranked by message-lens tokens (the sharper attribution); the tail is one collapsed row listing every consumer ×count — visible, never dropped.
- **Dual-lens honesty:** session lens covers sessions with known usage only, and first-day attribution is marked in the league note (a short window can zero session-lens counts). The 2.6k pruned-transcript calls with no grain are stated in a league footnote — unknown not zero, counted in the tiles, absent from the league. **Message-lens join is on `message_id` alone** (the #42 deferred call: API ids are globally unique; a session_id key adds nothing).
- **Errors/day spark colour: `--o-problem`, ruled deliberately.** The floor's "chart data ink only ever uses ink/spark tokens" governs *data* ink; the errors series encodes the problem semantic role, and red-over-blue-calls keeps the red-pairs-with-blue rule. Flagged by review; ruled, not missed.
- **hide-cache-reads reshapes the league's token columns**, not just the chart — cache-read dominance otherwise drowns the lens comparison.
- **Sunk cost:** project chips apply, the window doesn't (today's-filesystem scan); the measured median is styled as the authority figure on each project row; self-excluded count stated in the panel header; eager-stub subtotal keeps the delta pass's ~25 tok/entry estimate.
- **Hooks are user-scope:** window applies, chips don't — stated in the panel note. Latency columns on the models panel come from OTEL `api_request` (coverage stated); models unused since capture began read —.
- Top MCP server auto-opens when nothing is expanded; league/MCP/CLI/sunk expansion state survives filter re-renders.

**Review dispositions (code-review two-axis + ponytail-review, pre-commit):** the spec axis caught three real gaps, all fixed — first-day attribution unmarked, self-excluded count missing from the sunk header, and league "first/last used" window-scoped where the spec means all-time facts. Standards axis produced the `--o-problem` ruling above plus duplication cleanups (`addDays` shared via `hs`, `errHtml`/`bump` helpers). Ponytail: −1 line.

The what-view's axis-contrast flag and this view's floor conformance go to the audit ticket #47.


