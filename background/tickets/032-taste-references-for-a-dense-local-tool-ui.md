# #32 Taste: references for a dense local tool UI

state: closed · labels: wayfinder:research · opened: 2026-08-18 · closed: 2026-08-18

Part of #30

## Question

What references and vocabulary should seed the Diverge prompts? Gather ~8–12 strong references for data-dense, local-first tool UIs and observability dashboards, grouped by aesthetic family. Each entry carries: name + link, the vocabulary of what makes it work at 13px density (type choices, colour restraint, chart treatment, chrome weight), and a reusable one-line brief. Per family, a candidate guardrail list (what to ban). Scope is this product only — the reusable my-standards library is explicitly out of scope on the map. Findings land on a throwaway `research/taste-references` branch, resolution summary on this ticket.



---

**comment · 2026-08-18**

## Resolution

12 references across 5 aesthetic families, each entry grounded via web research in the product's current look and carrying vocabulary-at-13px, a reusable one-line brief, and floor-friction notes; each family carries a candidate guardrail ban list. Mapped 1:1 to the five Diverge candidates:

1. **Terminal instrument** (btop++, Berkeley Mono / U.S. Graphics) — box-drawn frames, braille-resolution sparklines, mono-only engineering-document chrome.
2. **Quiet dev-tool** (Vercel Geist, Linear, Raycast) — 10-step gray ladders, hairline borders, one accent; the proven centre of mass, guardrailed against looking like everyone else (no Inter).
3. **Observability workhorse** (Grafana, Honeycomb) — panel grammar, shared time axes, heatmap + select-to-compare small multiples; chrome refused, thresholds re-mapped off green/yellow/red.
4. **Editorial data journalism** (FT Visual Vocabulary, The Economist) — title-states-the-finding charts, blues-and-greys data ink, locked-scale small multiples; the contrarian candidate, and the most floor-native.
5. **Calm ledger** (Plausible, Tailscale admin, Stripe Dashboard) — one-page answers, bar-behind-text league tables, two-line cells, tint-shift depth; light-first counter-position to 1 and 3.

Cross-family notes cover the shared 30-day axis invariant, the why-view evidence-quote test, and honest empty/unresolved states.

Document: ../research/taste-references.md

