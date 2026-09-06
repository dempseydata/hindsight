# #37 Exit package: tokens in the repo, handoff to Build

state: closed · labels: wayfinder:task · opened: 2026-08-18 · closed: 2026-08-20

Part of #30

## Question

Close the map: pull the chosen design system into the repo (`/design-sync pull`, from VS Code), assemble the handoff bundle grill-with-docs consumes at the top of the styled Build effort — direction contract, UI stack reasoning, `design/design-inputs.md` — and turn Impeccable hooks back on. Resolution records where everything landed; the styled build opens as a fresh effort, not on this map.



---

**comment · 2026-08-20**

## Resolution

The exit package is on master (`ff3fb05`); Impeccable hooks are back on. The map is complete — no open wayfinder tickets remain.

**Where everything landed:**

- **`design/tokens.css`** — the V3 · Indigo deck direction contract as code: full palette, semantic roles with AA `-text` weights, chart-ink palette, faces, radius, elevation, motion. Single source of truth per [Decide the UI stack](036-decide-the-ui-stack.md); the server inlines it at render time.
- **`design/build-handoff.md`** — the bundle index grill-with-docs consumes at the top of the styled Build: direction reasoning (Diverge #34 → Narrow #35), the four UI-stack decisions ADR-ready, and the carry-alongs (why-view drop ADR, ADR-0001 clarifying note, nightly plist ticket, richer substrate scan, open judgement calls).
- **`design/design-inputs.md`** — already on master (ticket #33), referenced from the index.
- **Impeccable hooks: on** (`.impeccable/config.json` → `enabled: true`), per the map note; the floor audit itself belongs to Build.

**One honest deviation:** `/design-sync pull` had nothing to pull — no design-system project exists on claude.ai/design; the direction lives on the "Hindsight Narrow" canvas, which is an artifact, not a design-system project. The tokens were instead transcribed from [Narrow #35](035-narrow-one-direction-three-variants-one-winner.md)'s human-approved contract and **verified verbatim against `VariantIndigo.dc.html` on the canvas** — all 23 token values, faces and radii match the artboard exactly. Same outcome (tokens in the repo as committed code), different mechanism.

The styled build opens as a fresh effort with `grill-with-docs` on this bundle — not on this map.

