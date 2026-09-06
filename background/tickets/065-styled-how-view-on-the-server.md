# #65 Styled /how view on the server

state: closed · labels: wayfinder:task · opened: 2026-08-26 · closed: 2026-08-29

## Question

Build the real `/how` view on the on-demand server, per the greybox ticket's captured answers, within the shipped design system — `design/tokens.css` and the root DESIGN.md are the contract, no new direction-setting. Stack rules per ADR-0008 (stdlib server, read-only SQLite, zero-dep vanilla HTML/JS). Impeccable hooks back **on**.

Done when `/how` is live and browser-verified on real data: stage-anchored trail beside the stated-process panel for a declared project, graceful degradation verified on an undeclared one, mounted in the shared chrome's navigation.

Presentation judgement calls not settled by the greybox are decided inside this ticket against real data and recorded in the resolution comment.



---

**comment · 2026-08-28**

Design input landed: greybox #64 resolution (phase runs newest-first, status fact list per ADR-0012, stated-process panel, degraded states, project selector not chips, no shared chrome). Now blocked by the narrative pass so the view lands with its status card; two follow-ups recorded there for this ticket — drop `wayfinder` from Plan markers, decide `/clear` off-script handling.


---

**comment · 2026-08-29**

Amendment from #64: the project selector lists declaring projects only; no absent-state rendering. Invalid state (banner + error + trail) stays.


---

**comment · 2026-08-29**

## Resolution

Landed in 80e6268. `/how` is live on the on-demand server, in the nav, browser-verified (Playwright) on real data: hindsight (dense, valid), thisisme (sparse, valid), and hindsight with its declaration mangled (`skills:` → `skill:`, served from a scratch projects dir) for the invalid state. All within the shipped Indigo tokens; Impeccable hooks were on.

**What it is.** Server-rendered Python, no script — nothing on the page is interactive beyond the project selector, which is a link (`/how?p=`). Selector lists declaring projects only, busiest first; an unknown `?p=` says so and falls back. Status card: the stored Built / Reversed / Now narrative in a 2:1:1 grid over the mechanical line (current stage since-date, run tally, span, per-stage recurrence), **marked stale** when the row's ledger hash, prompt version or model no longer match the live ledger (ADR-0012 amendment); "no narrative yet" when no row exists. Phase runs newest first — stage, date or range, sessions (counted where titled, i.e. by majority, so counts and titles agree) · events (all in the band), audit titles, names used, minor-stage counts; the current run carries the accent rule. Stated-process panel at 260px as the greybox left it; off-script total with the distinct list collapsed; trail tally under both states. Invalid: caution-dashed banner with the parser's line and the file path, the trail grouped by session as the unbucketed lane, panel absent (there are no stages to state).

**Judgement calls decided here against real data:**
- **No per-stage hue.** The greybox colour-keyed runs to the panel with a seven-hue palette. The contract's only categorical ink is the four-step blue ramp; five stages on it are indistinguishable at 13px, and the accent, semantic and compare tokens may not carry stage identity. The stage label (bold, in the run's first column and the panel card) does the keying; the current run alone is accent-bordered (a 3px rule, not a surface).
- **Shared chrome absent**, as the greybox decided: title + nav + a one-line `cov` sentence, then the selector — no chips, chart or window controls, and no `CHROME_JS`.
- **`wayfinder` removed from hindsight's Plan markers** (ADR-0011 amended): 10 runs → 7, and the two 27 Aug ticket sessions now read Build, which they were. Consequence: the stored hindsight narrative is now stale on the page until the next nightly, which exercised that path on real data. thisisme and project-template still list it and want the same edit — their repos, not this one.
- **`/clear` (and now `wayfinder`) dominate off-script** — 138 events, of which the two session-openers are ~85. Left visible: a view-side drop hides, and an ignore list is an ADR-0011 change. Ticketed as a grilling question.
- **Fold threshold stays at 3.** At styled density the thin bands (the 4-event Build run of 27 Aug) read fine as runs; raising it would swallow the Plan↔Build alternation that is the view's texture.
- **Stale rule** checks all three regeneration keys, not just the hash, so a prompt bump never shows as current.

**Review.** `code-review` (standards: `--o-faint` text was below AA → `--o-dim`; inline style → class; ADR amendment recorded; DB values escaped) and `/ponytail-review` (Counter over hand-rolled tallies, duplicate selector CSS folded into the chrome rule, helper for names) both applied before commit. 121 tests green; `test_serve` covers the valid/stale, invalid, unknown-project and no-declaring-project paths through HTTP.


