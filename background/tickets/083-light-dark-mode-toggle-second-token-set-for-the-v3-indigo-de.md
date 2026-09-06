# #83 Light / dark mode toggle — second token set for the V3 Indigo deck; design revisited

state: closed · labels: needs-triage · opened: 2026-08-30 · closed: 2026-08-31

## Intent

A light / dark mode toggle for the served UI (what-view, where-view, how-view). The design is revisited as part of this ticket — light mode is a second palette, not a CSS filter over the dark one.

## What is already settled (inputs, not up for re-litigation)

- **ADR-0007**: V3 Indigo deck is the chosen direction — near-black indigo ground, elevated panels, periwinkle accent. Dark is the incumbent; light mode extends the direction, it does not reopen it.
- **`design/tokens.css` is the contract** — single source of truth, inlined by `build/serve.py` as `TOKENS_CSS` into every page. A light mode therefore lands as a second token set behind a selector; views change little or not at all. This makes the *implementation* seam small; the work is the palette.
- **The floor rules hold in both themes** (root `DESIGN.md` / house floor): every colour a named token, AA-passing text on surface at the sizes actually used, semantic ok/caution/problem set with red paired with blue (never green), chart data ink on its own palette, no runtime font fetches.

## Questions for the grilling session (not decided here)

- Toggle mechanics: follow system preference (`prefers-color-scheme`), a manual toggle, or both with manual override? Where does the preference persist (localStorage is the obvious home — server stores nothing per-viewer)?
- Is light mode a *derivation* of the indigo deck (same hues, inverted value structure) or does it get its own Narrow pass — 3 variants, pick one — per the design flow? my-process says a new surface runs the flow; a second theme is arguably a new surface.
- Sparklines / chart ink: the 30-day bar sparklines were tuned against a near-black ground — does the ink palette survive inversion or need its own light-mode ramp?
- Scope: all three views in one ticket, or land tokens + one view as the tracer bullet?
- Does `DESIGN.md` (re-derived from the shipped UI, ticket #52) get re-derived again after this lands?

## Route

Design-phase ticket. Session opens with `grill-with-docs` (decisions → ADR alongside ADR-0007/0008), then the design flow for the light palette (Claude Design Diverge/Narrow, taste-skill fallback), then implementation against `tokens.css`. Impeccable hooks stay ON — this is real palette work, not greybox.



---

**comment · 2026-08-31**

Grilling session complete (grill-with-docs, 2026-08-30). Decisions recorded in **ADR-0017** (`docs/adr/0017-light-theme-second-token-set.md`), pointer amendment in ADR-0007, vocabulary in `CONTEXT.md` ("Served UI": **theme**, **theme pin**).

Answers to the open questions:

- **Design pass** — mini-Narrow on the palette only: light tokens derived from the indigo deck, 3 variants compared in Claude Design with real content (real sparklines + stacked token chart in the comps). No Diverge; ADR-0007 not reopened.
- **Toggle** — three states: system (`prefers-color-scheme`) by default, manual header toggle overrides, pin in `localStorage`, applied pre-paint via inline script in shared chrome. Server stays read-only, stores nothing per viewer.
- **Chart ink** — full re-tune in the mini-Narrow: light ink ramp, spark, gapline, axis, stage hues; the three dark-tuned opacity washes (compare `.06`, selrule `.7`, pre-coverage `.22`) promoted to tokens with per-theme values. Floor re-verified against light values (AA `-text`, stage ≥6.5:1 on panel).
- **Scope** — all three views in one ticket. Fact-driven: zero colour literals outside `tokens.css`, so the token swap is atomic across views; a one-view tracer would cost more, not less.
- **DESIGN.md** — re-derived after landing; already mandated by ADR-0007's addendum, not a new decision.
- **Contract shape** — single `tokens.css`: dark `:root` verbatim, light behind `@media (prefers-color-scheme: light)` guarded `:root:not([data-theme=dark])` plus explicit `[data-theme=*]` blocks; `color-scheme` per block; `serve.py` seam untouched.

Next: the mini-Narrow in Claude Design, then implementation against `tokens.css`. Impeccable hooks stay on.



---

**comment · 2026-08-31**

Landed in ea32f1c. Mini-Narrow decided C · Ledger (ADR-0017 addendum); light token set + promoted washes in tokens.css; three-state pin toggle in every view; floor re-verified (worst text 5.18:1, stages ≥6.5:1 on light panel); DESIGN.md re-derived. Canvas: Hindsight Light Narrow.

