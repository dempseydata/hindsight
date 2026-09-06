# #47 Floor audit: /impeccable audit over the styled UI

state: closed · labels: wayfinder:task · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Run `/impeccable audit` over the finished styled UI and fix floor violations (named tokens only, semantic roles with AA `-text` weights, red pairs with blue, accent limits, chart data ink on its own palette, line-height ≥ 1.50 long-form, no runtime font fetches). Belongs to this Build effort per the handoff.


---

**comment · 2026-08-25**

## Resolution

`/impeccable audit` run over the full styled UI (serve.py chrome + what-view + where-view, tokens.css). The mechanical detector returned zero findings; the floor was verified by hand — every text/colour pairing's contrast ratio computed at the size actually used.

### Floor verdict: one violation, fixed

**Fixed** — the item #45 flagged forward: 9px chart-axis labels rendered in `--o-axis` (#6f7794), 3.99:1 on the panel — below the 4.5:1 AA text floor. Now `--o-dim` (7.02:1), matching #45's faint→dim precedent for small text. **tokens.css untouched** — the direction contract stays verbatim-verified; `--o-axis` remains in the contract for non-text chart lines. Commit e2a730f. 14/14 serve tests pass; detector clean after the fix.

All other floor rules verified passing:

| Floor rule | Verdict |
|---|---|
| Named tokens only | ✅ every colour via `var(--o-*)`; only literals are `transparent` + the elevation token's own `rgba()` |
| Semantic roles, AA `-text` weights on text | ✅ `.err` → `--o-problem-text` (8.5:1), entry code → `--o-ok-text` (9.1:1); bright weights only as spark fills (non-text, 6.5:1 ≥ 3:1) |
| Red pairs with blue, never green | ✅ ok = periwinkle blue; no green in the system |
| AA text at size used | ✅ after fix — dim 7.0:1, accent 6.7:1, all `-text` ≥ 8.5:1 |
| Accent never body text / large surfaces | ✅ links, active chips, ADR badge only; no accent backgrounds |
| Chart data ink own palette | ✅ ink-1..4 + spark; selection on compare hue. Error bars in `--o-problem` are #48's judged call (errors rendered *as* semantics), not re-litigated |
| Long-form line-height ≥ 1.50 | ✅ body 13/1.5, refusal pre 12/1.5; `font:` shorthand resets only on one-line labels |
| No runtime font fetches | ✅ system stacks only |

### Audit health score (non-floor dimensions, documented not fixed)

| Dimension | Score | Key finding |
|---|---|---|
| Accessibility | 3/4 | chart click-filtering is mouse-only (P2, below) |
| Performance | 4/4 | full re-render measured instant at 250 sessions (#45's judged call) |
| Responsive | 3/4 | desktop-only local tool by design; league grid overflows on narrow viewports (P3) |
| Theming | 4/4 | full token system, deliberate single dark look, explicit body background |
| Implementation integrity | 4/4 | coherent product-specific system; honesty annotations throughout |
| **Total** | **18/20** | Excellent |

**P2, appended to #50:** the chart's click-a-bar day columns are SVG rects with no keyboard access or ARIA — keyboard users can't reach day/range filtering. Workaround exists (window preset buttons cover the common cases), hence P2 not P1. P3s not filed (touch targets and narrow-viewport overflow on a desktop-only localhost tool; hover-only spark tooltips) — noise at this product's scale.


