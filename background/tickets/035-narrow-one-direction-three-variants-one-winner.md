# #35 Narrow: one direction, three variants, one winner

state: closed · labels: wayfinder:prototype · opened: 2026-08-18 · closed: 2026-08-20

Part of #30

## Question

Take the chosen candidate, generate three variants of it, pick one. Output is the direction contract the exit ticket packages: palette (every colour a named token, semantic ok/caution/problem roles with AA -text weights, red paired with blue, chart ink on its own palette), faces (no runtime fetches), radii, elevation, motion. This is where hues and faces get settled — they are an output of this ticket, never an input from the standard.


**Input from Diverge (#34):** the chosen candidate is **C · Observability workhorse**, carrying one graft from A — consumer-league sparks as bar sparklines (per-day bars on the shared 30-day axis), not heat strips. See #34's resolution comment and the canvas it links.



---

**comment · 2026-08-20**

## Prototype asset — three variants of C on canvas

Design canvas: https://claude.ai/code/artifact/74ca01e8-d31e-42e3-aa04-01d0efe0cc39

Three artboards, each the full Diverge-C page (same real content: Aug 16–17 ledger with the expanded ticket-#24 entry, 28-day stacked token chart with the real Aug 15 gap, consumer league, MCP servers, models, sunk-cost drill with the 56.4k measured-median authority figure, hook panel, coverage footer), all three carrying the A-graft: the consumer league's heat strips are replaced by **bar sparklines** — per-day bars on the shared 30-day axis, missing day rendered as a gap.

- **V1 · Slate console** — the judged winner as chosen: cool blue-slate ground, blue accent, flat hairline panels, 3px radii, system-ui.
- **V2 · Graphite ruled** — answers the Diverge note's chrome-gravity warning: warm graphite, panels dissolve into 2px-ruled sections, cyan accent, 0 radius, Avenir Next.
- **V3 · Indigo deck** — leans into the instrument: near-black indigo, elevated (shadowed) panels, 6px radii, periwinkle accent, 28px stat numerals.

Each artboard ends in a **direction-contract strip**: the full named-token palette (with hex values), faces, radii, elevation and motion — the winner's strip is what the exit ticket packages for the styled build. Floor upgrades applied to all three relative to the Diverge comp: the stray hex literals in the stacked chart/chips are now tokens, and ok/caution/problem text renders in explicit AA `-text` weights.

Each variant carries a sticky note with its honest motivation and main tradeoff.

**Open: the pick.** HITL — resolution is the human's comparative judgement, recorded here when made.


---

**comment · 2026-08-20**

## Resolution

**Winner: V3 · Indigo deck** — chosen comparatively against V1 · Slate console and V2 · Graphite ruled on the canvas (https://claude.ai/code/artifact/74ca01e8-d31e-42e3-aa04-01d0efe0cc39), identical real content in each. No amendments.

**The direction contract** (the exit ticket packages this from V3's contract strip; `VariantIndigo.dc.html` on the canvas is the reference):

- **Palette (named tokens):** `--o-bg #0b0d14` · `--o-panel #141826` · `--o-border #272e45` · `--o-text #dde2f0` · `--o-dim #9aa3bd` · `--o-faint #6f7794` · `--o-accent #7c9bff` (`--o-accent-ink #0b0d14`) · `--o-compare #f0b23f` (selection/compare hue)
- **Semantic roles:** ok `#7c9bff` / caution `#e3b859` / problem `#f27878`, each with an AA `-text` weight (`#a3b8ff` / `#eac878` / `#f79b9b`) — text always renders in the `-text` weight; red pairs with blue per the floor
- **Chart data ink (own palette, never accent/semantic):** `--o-ink-1…4` `#82a9e8` `#5c83c4` `#41639b` `#2b4468` · `--o-spark #82a9e8` · `--o-gapline #4c5470` · `--o-axis #6f7794`
- **Faces:** system-ui UI · ui-monospace/SF Mono numerals · 28px stat numerals — no runtime font fetches
- **Radii:** 6px · **Elevation:** panels lift on `--o-elev: 0 3px 10px rgba(0,0,0,0.45)` · **Motion:** 200ms ease hover lift on panels
- **Spark grammar (the A-graft, now standard):** bar sparklines, per-day bars on the shared 30-calendar-day axis, own peak per spark, missing day = gap, never zero

**Assets (flow step 6), judged here as the fog note directed:** none. The chosen direction has no imagery surface — every panel is data ink on tokens; there is no hero, no illustration slot. The assets step collapses to nothing and leaves the fog.

Carries to [Exit package: tokens in the repo, handoff to Build](037-exit-package-tokens-in-the-repo-handoff-to-build.md): pull/extract this contract into the repo and bundle it with `design/design-inputs.md`. [Decide the UI stack](036-decide-the-ui-stack.md) is unaffected by the pick.

