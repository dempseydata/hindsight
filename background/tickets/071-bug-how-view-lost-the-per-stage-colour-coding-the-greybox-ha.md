# #71 Bug: how-view lost the per-stage colour coding the greybox had

state: closed · labels: wayfinder:task · opened: 2026-08-29 · closed: 2026-08-29

## Question

The greybox (#64) colour-keyed each phase run to its stage in the stated-process panel; the styled build (#65) dropped it — the label alone keys the stage. Bring the colour coding back: each declared stage gets a hue, carried on the panel card and the run band's rule, consistent across the page.

The constraint #65 tripped on, to decide here rather than dodge: the contract has no categorical palette. The ink tokens are a four-step blue ramp (`--o-ink-1..4`) — sequential, not categorical, and short of five stages; accent/compare/semantic tokens may not carry identity (floor rules in `design/tokens.css`). So this is a small design-contract extension: add a stage palette to `design/tokens.css` (and the root DESIGN.md sidecar), distinct at 13px on `--o-panel`, never reused for chart data or semantics, and record it as an amendment to ADR-0007. Six hues is enough (five stages plus an off-script grey); a project declaring more cycles.

Done when hindsight and thisisme render with stage hues on both sides, `/impeccable audit` in #69 runs over the result, and the palette is in tokens.css not HOW_CSS.


---

**comment · 2026-08-29**

## Resolution

Landed in c1595a6.

**Palette** — `design/tokens.css` gains a stage group: `--o-stage-1..5` (teal #2fc4c4, violet #a98cf5, magenta #e07ad8, orange #f0995a, gold #d4c95a) and `--o-stage-off` (#6f7794). All five ≥6.5:1 on `--o-panel`; the off grey is 3.99:1, fine for a non-text rule. Assignment is **positional**: a declaration's stages take `-1..-5` in declared order and cycle past five — identity is per project, not per stage name.

**Carried as** the 3px left rule on each stated-process card (dashed when nothing observed) and each phase-run band, via an inline `--stage` custom property set by `_hue()`; the CSS falls back to `--o-stage-off`, which is what the unbucketed (invalid-declaration) lane gets. No colour literal in view code; `HOW_CSS` holds no palette.

**Consequence** — the current run's accent rule had to go so the rule could carry the stage; it is now a small accent `now` badge beside the stage name.

**Recorded** — ADR-0007 amendment (stage hues are non-text marks only; never chart data, never semantic, and the reverse); `DESIGN.md` + `.impeccable/design.json` re-derived by the documenter ("Stage Identity" section, "The Stage-Rule Rule").

**Verified** — browser-rendered on hindsight (all five stages observed) and thisisme (Build/Release dashed, hued): hues on both sides, consistent across the page. Test suite green (`test_serve` asserts hue + badge on the fixture).

**Judgement calls, from review**
- Gold (`-5`) sits near `--o-caution`, which does appear on `/how` (stale text, invalid-declaration dashed border). Kept: a solid 3px rule beside the stage label against dashed caution furniture is not confusable at 13px, and the six-hue space excluding blue, green, red and amber is tight. If it reads as caution in use, swap `-5` — `/impeccable audit` in #69 is the place to judge it.
- `--o-stage-off` shares its literal with `--o-faint`/`--o-axis`, so an unbucketed band's left rule vanishes on hover. Accepted; it is the unbucketed lane.
- `.impeccable/design.json` is untracked (pre-existing) — the "sidecar re-derived" claim lives only on disk. Worth a `git add .impeccable/design.json` decision outside this ticket.


