# #41 Grill-with-docs: interrogate the handoff bundle and write the design ADRs

state: closed · labels: wayfinder:grilling · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Run `grill-with-docs` over the definition and the design handoff bundle (`design/build-handoff.md`, `design/design-inputs.md`, `design/tokens.css`). The seam at the top of Build: interrogate, then write what is currently ADR-ready but ADR-absent —

- the v1 scope / why-view drop ADR (#39), plus CONTEXT.md's "three views" framing update;
- the direction ADR (V3 · Indigo deck — family, look, spark grammar, no-assets call);
- the UI-stack ADR (#36 — foreground server, zero-dep vanilla UI, tokens-are-code, two refresh controls kept separate);
- the one-line clarifying note on ADR-0001's "schedules nothing" sentence (scheduled invocation ≠ background process).

HITL — one question at a time; the agent never answers its own questions.


---

**comment · 2026-08-25**

## Resolution

The seam is written. Grilling settled two open calls; everything else was captured faithfully from #39/#36 and the handoff bundle. Commit `a0aeb5c`.

**Written:**
- **ADR-0006 — v1 ships two views; the why-view is dropped wholesale** (#39): the near-duplication observation, the four counter-arguments set aside, what dies (surface, why-pass pipeline, eval burden) and what stays (backstop capture unrendered, shared chrome); the future fold-in idea recorded, not planned.
- **ADR-0007 — Direction: V3 · Indigo deck; tokens.css is the contract** (#34→#35): family, look, spark grammar, no-assets call; values verified 2026-08-20 against `VariantIndigo.dc.html`.
- **ADR-0008 — UI stack** (#36): foreground stdlib `http.server` (strictly read-only), zero-dep vanilla UI with ADR escape hatch, tokens-are-code, two refresh controls kept separate; the server never grows a run button.
- **ADR-0001 amendment (2026-08-24):** "schedules nothing" constrains the *listener* — a launchd calendar job invoking the on-demand analysis is a scheduled invocation, not a background process.
- **CONTEXT.md:** opener reframed to two views in v1; `resolution` dropped from the analysis-run pipeline line; run record kept (moved up, reworded); change-event entry notes v1 renders/links nothing.

**Grilled decisions (operator):**
1. **CONTEXT.md pruned now, wholesale** — Findings-and-evidence and Evaluation sections deleted; why-pass, anti-capture restatement, sidecar map, deterministic linking removed; model pin and prompt version reworded without the dead regression-gate mechanism. Glossary deliberately ahead of the code until #43 lands.
2. **The unwatched-canvas re-verification rule is recorded in ADR-0007**, not left to die with the map: any later canvas edit requires re-verifying tokens.css verbatim against the winning artboard.

**Map housekeeping surfaced en route:** #46 closed as a botched creation (heredoc debris in its body; #48 is the clean, properly wired where-view ticket), and the nightly-plist ticket its debris had swallowed now exists as #49 (unblocked).

