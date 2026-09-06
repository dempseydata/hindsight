# Taste references — dense local tool UI

Resolution of [#32](../tickets/032-taste-references-for-a-dense-local-tool-ui.md), part of map [#30](../tickets/030-map-hindsight-design-validated-greyboxes-to-a-chosen-directi.md). Product-scoped: these references seed hindsight's Diverge prompts only — the reusable my-standards taste library is explicitly out of scope.

**What hindsight is, for calibration:** three views over Claude Code history — a what-view (audit ledger, one collapsed row per session), a why-view (day-ledger change timeline with evidence quotes), a where-view (panel dashboard: token league tables, sparklines on a shared 30-day axis, sunk-cost tree drill). Single user, local-first, read at 13px. No marketing surface. The reference bar is therefore: *does this hold up at 40 real rows on one screen*, not *does this demo well*.

**How to use:** one family per Diverge candidate, prompt shape *aesthetic · reference · intent · guardrails*. Each entry carries a one-line brief slotting into that shape; each family carries the guardrail list for its candidate. Never stack families in one candidate.

**Floor rules bind every comp regardless of family** (from my-process / map #30): every colour a named token; ok/caution/problem semantic roles with AA `-text` weights; red pairs with **blue**, never green; AA contrast at the size actually used; chart data ink gets its own palette, never brand or semantic colours; long-form line-height ≥ 1.50; no runtime font fetches. Where a reference violates the floor, the entry says so — take the vocabulary, not the violation.

---

## Family 1 — Terminal instrument

Box-drawn, monospaced, dark-by-default. The UI as a piece of test equipment: static layout, everything visible at once, data rendered in sub-cell resolution (braille, blocks). Natural fit for hindsight's density — a TUI never had the option of whitespace-as-luxury — and for the operator's actual habitat, since the data *is* terminal history.

### btop++
<https://github.com/aristocratos/btop>

- **Vocabulary:** modular boxes (cpu / mem / net / proc) in Unicode box-drawing frames; braille-character graphs — the highest-resolution sparkline treatment anywhere, history and instant reading in one strip; 24-bit truecolor gradients that darken with intensity; themed but structurally rigid — themes swap palette, never layout; process list as the dense-table anchor with inline per-row graphs.
- **At 13px:** density comes free — the cell grid *is* the layout system; hierarchy is done with colour weight and frame titles, not size, because size is fixed.
- **Floor friction:** its truecolor gradients are continuous, not named tokens — a comp in this family must quantise gradients into a stepped, tokenised data-ink ramp. Its green/yellow/red load colouring violates red-pairs-with-blue.
- **Brief:** *A btop-style instrument panel: box-drawn frames, braille-resolution sparklines, stepped data-ink ramp, layout fixed as a cockpit.*

### Berkeley Mono / U.S. Graphics Company
<https://usgraphics.com/products/berkeley-mono>

- **Vocabulary:** "functional first" monospace positioned as vintage-instrument nostalgia done rigorously — CRT glow, rotary-encoder tactility, "the calm of static user interfaces"; the U.S. Graphics site itself is the reference: engineering-document chrome, part numbers (TX-02), rule lines, no decoration that isn't a label. This is the type voice of developer-brutalism.
- **At 13px:** a mono face designed for exactly this size band; tabular by construction, so league tables and token counts align without effort; hierarchy via weight and case (ALL-CAPS section labels), not face changes.
- **Floor friction:** commercial licence — if chosen it must be bought and bundled locally (no runtime font fetch is a floor rule anyway). The page itself is behind a 403 to scripted fetch; vocabulary above is grounded in its published positioning and coverage.
- **Brief:** *An engineering-document UI in a single instrument-grade mono face: rule lines, part-number labels, ALL-CAPS section headers, zero decorative chrome.*

**Family 1 guardrails (ban list):** no Inter or any humanist sans anywhere; no rounded corners > 2px; no shadows or elevation — depth is frames and rules only; no continuous colour gradients (stepped token ramps only); no green/yellow/red status triads (red+blue per floor); no faux-CRT effects (scanlines, glow, chromatic aberration) — the nostalgia is structural, not cosmetic; no proportional face smuggled in for "readability".

---

## Family 2 — Quiet dev-tool

The Geist/Linear/Raycast school: near-monochrome surface ladders, hairline borders, one restrained accent, dark theme as first-class. The dominant contemporary look for developer tools — the safe centre of mass, which is both its strength (proven at density) and its risk (the Diverge candidate most likely to look like everything else).

### Vercel Geist
<https://vercel.com/geist> · colours: <https://vercel.com/geist/colors>

- **Vocabulary:** a 10-step gray scale with *assigned roles per step* — 1–3 backgrounds, 4–6 borders, 7–8 high-contrast fills, 9–10 text/icons; nine accent scales (blue, red, amber, green, teal, purple, pink…) each with the same 10-step structure; Geist Sans + Geist Mono pairing; "presets for radii, fills, strokes, and shadows"; P3 colour on capable displays. The most token-disciplined system in this document — its structure is the floor rule "every colour a named token" made flesh.
- **At 13px:** hierarchy carried almost entirely by the gray ladder (secondary text = step 9, primary = step 10); borders one step, backgrounds another — never improvised; mono face reserved for data values.
- **Floor friction:** none structurally — this family is the easiest to make floor-compliant. Discipline point: hindsight's chart data ink must still be a separate palette, not the nine accent scales doing double duty.
- **Brief:** *A Geist-grade token system: 10-step gray ladder with assigned roles, hairline borders, sans for chrome and mono for values, one accent that never carries surfaces.*

### Linear
<https://linear.app>

- **Vocabulary:** restraint as the whole aesthetic — neutral foundation, accent only on interactive elements; subtle shadow instead of borders ("elements float rather than being framed"); dark mode preserving the same contrast hierarchy; typographic hierarchy by weight and scale, generous line spacing. The canonical proof that an issue tracker — rows, statuses, metadata, exactly hindsight's what-view shape — can be dense *and* calm.
- **At 13px:** list rows carry five or six fields without visible gridlines — separation by spacing rhythm and text-weight steps; icons at text size do the work of a column of labels.
- **Floor friction:** none inherent; note Linear's depth-by-shadow conflicts with Family 1's frames — a reason these are different candidates.
- **Brief:** *Linear-calm ledger rows: no gridlines, hierarchy by weight and spacing rhythm, accent only where the cursor can go.*

### Raycast
<https://www.raycast.com> · themes: <https://manual.raycast.com/themes>

- **Vocabulary:** near-total darkness (#040506 void) with surfaces as "barely-lighter charcoal strata" (#07080a → #0d0d0d → #101111) rather than cards; hairline 1px borders, 6–10px radii; keyboard-first — every action's shortcut documented inline, which is itself a density device; multi-layer shadows as tactile "pressable" cues; brand red (#FF6363) used sparingly as signal, not CTA.
- **At 13px:** the compact list is the whole product — icon, title, subtitle, accessory, shortcut in one 36px row; hover as opacity shift, not colour swap.
- **Floor friction:** uses Inter (with ss03) — this family's guardrails ban it (see below); its red-as-signal must be re-mapped so red means *problem* only, paired with blue per the floor.
- **Brief:** *Raycast-dark strata: charcoal surface ladder, hairline borders, inline keyboard affordances, one signal colour that means exactly one thing.*

**Family 2 guardrails (ban list):** no Inter (the centre-of-mass giveaway; both the impeccable detector and this map's own prompt examples flag it — pick a distinct sans); no purple gradients or any hero gradient; no glassmorphism / backdrop blur; no card-in-card nesting — one surface ladder, flat; no accent-coloured body text; no shadow *and* border on the same element — pick the family's one depth device and hold it.

---

## Family 3 — Observability workhorse

Grafana/Honeycomb: the incumbent genre for exactly hindsight's where-view. Panel grids, threshold colouring, query-shaped interaction. Worth studying precisely because hindsight must *not* become it — these tools are multi-tenant, config-heavy, and chrome-laden in ways a single-user local tool need not be. Mine the chart treatments; refuse the chrome.

### Grafana
<https://grafana.com> · Grafana 12: <https://grafana.com/blog/grafana-12-release-all-the-new-features/>

- **Vocabulary:** the panel grid as organising unit — every visualisation a titled, bordered rectangle on a dark canvas; Grafana 12's "dynamic dashboards" rebuilt layout adaptivity and split panel options from viz config; experimental theme packs (Tron, Gloom, Sapphire dusk…) demonstrating palette-swap over fixed structure; the genre's vocabulary of stat tiles, threshold bands, and shared time axes — the last being exactly hindsight's shared 30-day sparkline axis.
- **At 13px:** legends, axis labels and stat-tile units all live at 11–13px on dark ground — the genre proves AA-at-small-size is achievable but only with deliberate contrast steps.
- **Floor friction:** classic Grafana thresholds are green→yellow→red, directly violating red-pairs-with-blue; its default palettes mix semantic and data ink freely. Take the panel/shared-axis grammar, re-colour from scratch.
- **Brief:** *Grafana's panel grammar without its chrome: titled panels on a shared time axis, stat tiles with units, thresholds re-mapped to blue/red.*

### Honeycomb
<https://www.honeycomb.io> · BubbleUp: <https://www.honeycomb.io/platform/bubbleup>

- **Vocabulary:** the heatmap as first-class citizen — density itself made visible rather than averaged away; BubbleUp's interaction grammar: draw a box on the anomaly, get ranked small-multiple histograms comparing inside-the-box vs baseline, sorted by difference. The best existing answer to "why is this different?" as a UI gesture — directly relevant to the why-view's job and the sunk-cost drill.
- **At 13px:** ranked small multiples with one-line captions — dozens of tiny charts legible because every one shares scale and shape; colour carries only in-selection vs baseline, a two-hue discipline.
- **Floor friction:** none structural; its comparison colouring (often orange/blue) adapts cleanly to a tokenised two-hue data-ink pair.
- **Brief:** *Honeycomb's comparison grammar: heatmap for density, select-to-compare, ranked small multiples on shared scales, two-hue data ink.*

**Family 3 guardrails (ban list):** no multi-tenant chrome — no sidebar-of-sidebars, no org switchers, no panel edit affordances in view mode; no green/yellow/red threshold triads; no per-panel palette improvisation — one data-ink ramp and one comparison pair, tokenised, everywhere; no gauge/donut/speedometer tiles; no dashboard-as-wall-of-equal-panels — hierarchy between panels is mandatory.

---

## Family 4 — Editorial data journalism

FT/Economist chart language applied to an interface: charts that read like sentences, with typographic titles doing the analytic work. The contrarian candidate — almost no tool UI looks like this, which is exactly why it belongs in a five-way Diverge. Hindsight's views are *narratives about history* (what happened, why it changed), which is the one framing where editorial grammar beats instrument grammar.

### FT Visual Vocabulary
<https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary>

- **Vocabulary:** chart form chosen by *relationship* (deviation, ranking, change-over-time, part-to-whole…) — a taxonomy, not a gallery; space-efficient forms the dashboard genre ignores: ordered strip-plot dots for ranks across categories (a direct candidate for the token league table), slope charts, dot-strip timelines; annotation layered on the chart instead of legends beside it.
- **At 13px:** editorial charts assume print-column widths — small — so every form in the vocabulary already works at panel size; labels sit on the data, killing the legend round-trip.
- **Floor friction:** FT house style lives on the paper's salmon-pink ground — adjacent to the cream palette this project's own prompt examples ban; take the forms, not the newsprint.
- **Brief:** *FT visual-vocabulary forms in a tool shell: strip-plot ranks, slope changes, dot timelines, annotations on the data, no legends.*

### The Economist — Graphic detail
<https://www.economist.com/graphic-detail> · style notes: <https://fountn.design/resource/the-economist-visual-style-guide/>

- **Vocabulary:** a fixed editorial chart kit — neutral greys and *blues* as the working palette (note: the floor's red-pairs-with-blue rule is native here), red reserved as the brand mark; short left-aligned titles with descriptive subtitles doing the "so what"; thick white gridlines *through* the data rather than grey lines behind it; y-axis labels on the right; small multiples on locked shared scales — the stated Economist/FT discipline, and precisely hindsight's shared-30-day-axis rule.
- **At 13px:** title-as-finding means the chart can shrink further — the reading is in the words; one hue family plus emphasis colour keeps tiny charts legible.
- **Floor friction:** minimal — this is the most floor-native reference in the document. Its single brand-red accent must not leak into semantic use.
- **Brief:** *Economist-kit panels: title states the finding, blues-and-greys data ink, white gridlines through the data, small multiples on locked scales.*

**Family 4 guardrails (ban list):** no cream/salmon paper grounds (cream-palette detector; keep the ground neutral); no serif body text at data sizes — editorial voice lives in titles only; no legends where direct labels fit; no unshared y-axes across small multiples, ever; no decorative chart flourishes (drop shadows on bars, 3D, rounded bar caps); red never used for emphasis — it is either the problem role or absent.

---

## Family 5 — Calm ledger

Plausible/Tailscale/Stripe: the "boring on purpose" school — light-first, near-monochrome, one screen that answers the question without navigation. The strongest counter-position to Families 1 and 3: hindsight as a *statement you read*, not a cockpit you monitor. Fits the actual usage pattern — an on-demand analysis run reviewed occasionally, not a wall of live monitors.

### Plausible Analytics
<https://plausible.io> · dashboard tour: <https://plausible.io/docs/guided-tour>

- **Vocabulary:** the single-page dashboard as thesis — one visitors chart, top-N lists, and that is the product; "no sub-menus, no custom report builder"; top-N lists as horizontal bar-behind-text rows — the densest league-table treatment going, label + value + proportion in one 24px line; tidy enough that "boss-friendly screenshots require minimal cropping".
- **At 13px:** the bar-behind-text list carries three data dimensions with zero chart chrome; metric headline row (big number + delta) gives instant hierarchy above the fold.
- **Floor friction:** none notable; its accent-tinted proportion bars must come from the data-ink palette, not brand accent, under the floor.
- **Brief:** *Plausible's one-page answer: headline metrics, bar-behind-text league tables, one chart, nothing that needs navigation.*

### Tailscale admin console
<https://login.tailscale.com/admin/machines> · reference screens: <https://mobbin.com/explore/screens/bedfacb1-958b-40df-999d-308e76d8401f>

- **Vocabulary:** an infrastructure tool that reads like a directory listing — the Machines table: name, addresses, OS/version, last-seen, status dot, per-row overflow menu; metadata as quiet stacked second lines inside cells rather than extra columns; tag chips for classification; connectivity as a small coloured dot, the minimum viable status treatment; the design system deliberately consistent from console to clients.
- **At 13px:** two-line cells (primary + muted secondary) double column capacity without widening the table — directly applicable to the what-view's collapsed session rows.
- **Floor friction:** status dots must map to the ok/caution/problem roles with AA `-text` companions — a lone 8px dot cannot carry AA meaning by colour alone; pair with text as Tailscale itself does.
- **Brief:** *Tailscale-table calm: two-line cells with muted metadata, status as dot-plus-word, chips for tags, no gridline heavier than a hairline.*

### Stripe Dashboard
<https://stripe.com> · breakdown: <https://www.925studios.co/blog/stripe-dashboard-design-breakdown>

- **Vocabulary:** "near-monochrome financial-instrument language" — cool-white canvas, deep navy headings, one vivid indigo that alone earns button/link/icon-stroke duty; light typography weights even at display sizes ("confident restraint"); **no shadows — depth from background tint shifts**, moving toward a card-less system; precise microcopy and information hierarchy as the trust device; charts as thin unornamented lines with the number, not the plot, as the headline.
- **At 13px:** tabular numerals and tint-shift row separation keep money tables legible without rules; the number-first, chart-second hierarchy suits token totals.
- **Floor friction:** single-accent-does-everything must be split under the floor — the accent may not carry chart data ink; Stripe's own restraint makes the split easy.
- **Brief:** *Stripe-ledger restraint: tint-shift depth instead of shadows, number-first panels, one indigo-class accent confined to interaction.*

**Family 5 guardrails (ban list):** no dark-theme-first (this family's identity is paper-light; dark is the derived theme); no dashboard sprawl — if it needs a second screen per view, it has failed the family; no shadows (tint shifts only); no big-number tiles without their comparison delta; no accent colour on data ink or large surfaces; no Inter-by-default — restraint in colour does not license the default face.

---

## Cross-family notes for the Diverge ticket

- **Five candidates, five families** — the mapping is 1:1 by design; do not blend families within a candidate.
- **Real data everywhere** (map rule): each comp gets the delta-pass data — 40 real session rows, real token counts, a real unresolved-evidence row — because half these aesthetics only fail at real density.
- **Shared 30-day axis** is the one layout invariant every family must absorb: Economist locked scales, Grafana shared time axis, and btop history strips are the three treatments of it worth stealing.
- **The why-view's evidence quotes** are the hardest test: verbatim transcript text inside a dense timeline. Families 1 (mono, native) and 4 (editorial quotation) handle it naturally; Families 2/3/5 need an explicit treatment in their comps.
- **"Evidence not located" and coverage-window honesty** are first-class states, not error styling — every comp must show one, per the greybox resolutions.
