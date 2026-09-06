# ADR-0017: Light theme — derived second token set, three-state toggle, one contract file

**Date:** 2026-08-30 · **Status:** accepted · **Decides:** [issue #83](../../background/tickets/083-light-dark-mode-toggle-second-token-set-for-the-v3-indigo-de.md) (grilling session)

## Context

ADR-0007 settled the direction (V3 · Indigo deck) with dark as the shipped incumbent, and `design/tokens.css` as the sole contract, inlined by the server into every page. Ticket #83 adds a light theme and left four questions open: design process, toggle mechanics, data-layer treatment, and scope.

Facts that shaped the decisions: **zero colour literals exist outside `tokens.css`** — every view renders through `var(--o-*)`, so a second token set reaches all three views at once; the only theme-sensitive values outside the contract are three opacity washes (compare wash `.06`, selection rule `.7`, pre-coverage shading `.22`) and the hardcoded `color-scheme: dark`.

## Decision

1. **Light is a derivation, chosen comparatively — a mini-Narrow on the palette only.** Light tokens are derived from the indigo deck (same hues and roles, inverted value structure), then 3 variants of that derivation are compared in Claude Design with real content, one picked. No Diverge: a second theme of the same layouts is not a new surface, and ADR-0007's direction is not reopened. The comps must include real sparklines and the stacked token chart — "does the ink ramp read on white" is unanswerable from swatches.
2. **Three-state toggle.** `prefers-color-scheme` by default; a manual header toggle overrides; the pin persists in `localStorage` and is applied before first paint by a small inline script in the shared chrome. The server stays strictly read-only (ADR-0008) and stores nothing per viewer — the pin is per-browser, by design.
3. **Single contract file.** `tokens.css` remains the sole contract and gains the light set internally: the dark `:root` block stays verbatim (zero diff to the shipped look); light lands behind `@media (prefers-color-scheme: light)` guarded `:root:not([data-theme=dark])`, plus explicit `[data-theme=light]` / `[data-theme=dark]` blocks so the pin wins in both directions; `color-scheme` becomes per-block. No second file: ADR-0007's "never forked" holds, and a future token addition remains a single edit. The server's inlining seam is untouched.
4. **Full data-layer re-tune.** The light set re-tunes chart ink (`--o-ink-1..4`, spark, gapline, axis) and the stage hues; the three wash opacities are promoted to tokens with per-theme values. The floor is re-verified against the light values before the winning variant is accepted — AA `-text` weights at rendered sizes, stage hues ≥6.5:1 on the light panel, red-with-blue, accent never on body text or large surfaces. Same bar, second theme.
5. **Scope: all three views in one ticket.** Fact-driven, not preference: with no literals outside the contract, the token swap is atomic across views — a one-view tracer would require adding per-view scoping that the ticket would then delete.

## Consequences

- `DESIGN.md` and its sidecar are re-derived after landing (documenter re-run), per ADR-0007's addendum — mechanical, not a new decision.
- ADR-0007 carries a one-line pointer to this ADR; direction facts stay there, theme facts here.
- The pin does not roam: a different browser or a cleared profile falls back to *system*. Accepted — the server rendering identically for everyone is worth more than a roaming preference.
- Vocabulary: **theme** (dark / light), **theme pin**, three toggle states — recorded in `CONTEXT.md` under "Served UI".

## Addendum (2026-08-31): variant chosen

The mini-Narrow ran on the "Hindsight Light Narrow" canvas — three derivations
(A · Indigo wash, B · Porcelain, C · Ledger) with identical real content: the
30-day stacked token chart, 14-day tiles and consumer-league sparks from
`local-data/hindsight.db`. **C · Ledger** was picked: white ground (`#fcfcfe`),
recessed indigo panels (`#f1f3f9`), borders over elevation (`--o-elev: none`).
Floor re-verified numerically before acceptance: worst text contrast 5.18:1
(≥4.5 at rendered sizes), every stage hue ≥6.5:1 on the light panel, compare
4.53:1 on panel, red still pairs with blue. The promoted wash tokens carry
`.12 / 1 / .35` in light against `.06 / .7 / .22` in dark. The winning artboard
stays as `design/light-narrow/Main.dc.html` — reference-only, per ADR-0007;
`tokens.css` remains the contract.
