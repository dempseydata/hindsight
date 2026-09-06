# #30 Map: hindsight design — validated greyboxes to a chosen direction

state: closed · labels: wayfinder:map · opened: 2026-08-18 · closed: 2026-08-20

## Destination

A chosen visual direction for hindsight's tool UI — palette, faces and tokens settled and pulled into the repo, the UI stack decided, and the design-inputs consolidated — ready for the styled Build effort to open with grill-with-docs. Tool UI only: **two views — what and where** — plus shared header chrome. (Was three; the why-view was dropped from v1 by [Scope: drop the why-view from v1](039-scope-drop-the-why-view-from-v1.md).)

## Notes

- Consult: `CONTEXT.md`, `docs/adr/0001–0005`, the greybox resolutions ([what-view #5](005-greybox-the-what-view-audit-log.md), [why-view #6](006-greybox-the-why-view-change-timeline.md), [where-view #12](012-greybox-the-where-view.md)), and my-process's Design section. This map runs that flow with the wireframe step **skipped** — the greyboxes plus the delta pass cover it.
- **Claude Design is the default tool** for Diverge / Narrow / System; taste-skills and Open Design are fallback. Run `/design-sync` from VS Code only, never alongside a Desktop session on this repo.
- **Impeccable hooks OFF during prototype tickets** (`/impeccable hooks off`); back on at the exit ticket.
- **Real data everywhere** — comps carry real content from the delta-pass data, never lorem ipsum.
- One taste-skill variant per candidate, never stacked. Prompt shape: aesthetic · reference · intent · guardrails (guardrails are per-direction, e.g. "no Inter, no purple gradients" — never in the standard).
- Floor rules bind every comp: every colour a named token; ok/caution/problem roles with AA `-text` weights; red pairs with blue, never green; accent never carries body text or large surfaces; chart data ink gets its own palette; line-height ≥ 1.50 long-form; no runtime font fetches. DESIGN.md v1.2's Mintlify-derived look is explicitly **not** followed.
- One ticket per session (research excepted). Plan, don't do — the AFK task/research tickets are the only execution this map carries.

## Decisions so far

- [Taste: references for a dense local tool UI](032-taste-references-for-a-dense-local-tool-ui.md) — 12 references across 5 families (terminal instrument, quiet dev-tool, observability workhorse, editorial data journalism, calm ledger), one family per Diverge candidate, on research/taste-references
- [Delta pass: greyboxes re-judged on the real backend](031-delta-pass-greyboxes-re-judged-on-the-real-backend.md) — all three winners survive, no layouts reopened; hook panel real (placeholder retired); #6 noise policy provisionally settled pending real churn; consumer-league grain becomes a build requirement (richer substrate scan); refusal audit rows → defect #38; riders (chip policy, coverage-gap form, tree framing, extraction redundancy) to the Design-inputs bundle
- [Scope: drop the why-view from v1](039-scope-drop-the-why-view-from-v1.md) — v1 is two views (what, where); why-pass pipeline + its eval burden die at Build; backstop capture stays, renders nowhere in v1; why-specific riders from #31 (noise-policy re-check, evidence anatomy, extraction redundancy) are void; shared header chrome unaffected; ADR at Build handoff
- [Consolidate the Design-inputs bundle](033-consolidate-the-design-inputs-bundle.md) — `design/design-inputs.md` on master: shared header chrome, spark system, what-ledger and where-dashboard specifics, honesty rules; why-view inputs pruned per #39; styled-build judgement calls and grill-with-docs carry-alongs listed
- [Diverge: five candidate directions](034-diverge-five-candidate-directions.md) — winner: C · Observability workhorse (Grafana/Honeycomb — titled panels, stat tiles, shared 30-day axis, blue/red thresholds), with one graft from A: consumer-league sparks as Terminal-instrument bar sparklines, not heat strips; judged on a five-candidate canvas with identical real content

- [Narrow: one direction, three variants, one winner](035-narrow-one-direction-three-variants-one-winner.md) — winner: V3 · Indigo deck (near-black indigo, elevated 6px panels, periwinkle accent, 28px stat numerals, bar-spark grammar); full token contract in the resolution; assets step judged: none needed

- [Decide the UI stack](036-decide-the-ui-stack.md) — on-demand foreground stdlib server reading SQLite live (read-only, never invokes the model); zero-dep vanilla UI, exceptions ADR-gated; tokens land as committed tokens.css (comps reference-only); where-view refresh = browser reload, analysis = CLI + new nightly launchd job (fact corrected: none existed); ADR-0001 clarifying note carried to grill-with-docs

- [Exit package: tokens in the repo, handoff to Build](037-exit-package-tokens-in-the-repo-handoff-to-build.md) — `design/tokens.css` (V3 contract, verified verbatim against the canvas artboard) + `design/build-handoff.md` (direction & UI-stack reasoning, carry-alongs) on master at `ff3fb05`; Impeccable hooks back on; design-sync pull collapsed to verified transcription (no design-system project existed). **The map is complete** — the styled Build opens as a fresh effort with grill-with-docs on the bundle.

## Not yet specified

*Empty — the fog is cleared; the handoff bundle's form was settled by the exit ticket.*

## Out of scope

- The why-view — dropped from v1 wholesale by [Scope: drop the why-view from v1](039-scope-drop-the-why-view-from-v1.md): surface, why-pass pipeline, and eval burden. Backstop capture stays but renders nowhere in v1; pipeline removal is a Build-effort ticket.
- The styled build itself, live tweaking (`/impeccable live`) and the floor audit — those belong to the Build effort this map hands off to.
- Any marketing/landing surface — stays with post-personal-utility packaging (already out of scope on the v1 map).
- The cross-product taste reference library in my-standards — deliberately kept a separate future effort; this map takes only a product-scoped reference pass.
- Pipeline defects, including [#29](029-live-sessions-get-permanently-truncated-extracts-analysis-of.md) (live-session truncated extracts) — build bugs, not design.
- Writing the design ADRs — grill-with-docs does that at the top of Build; this map hands it the reasoning.










---

**comment · 2026-08-20**

Map complete: all tickets resolved, fog cleared, exit package on master (`ff3fb05`). The styled Build opens as a fresh effort — grill-with-docs on `design/build-handoff.md`.

