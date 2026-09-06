# #6 Greybox the why-view (change timeline)

state: closed · labels: wayfinder:prototype · opened: 2026-08-01 · closed: 2026-08-03

## Question

What does an evidence-linked setup-evolution timeline look like at real volume? Greybox on real harness findings (s380/d9c0/co23 outputs regenerated locally). Must answer: how does an entry show change + driver + verbatim evidence span without drowning the timeline? How do model-detected and mechanically-detected (no-rationale) changes read side by side? Impeccable hooks off.

Part of #1



---

**comment · 2026-08-01**

Delegated here by [Decide the silent-change backstop](004-decide-the-silent-change-backstop.md): the render-time noise policy for mechanical change entries — how to collapse high-frequency churn (e.g. settings.local.json permission-allowlist appends) without hiding real signal. Capture stores everything; the greybox on real data decides the display policy.


---

**comment · 2026-08-03**

Greybox built — awaiting reaction (this comment is a pointer, not the resolution).

**Run:** `git checkout prototype/why-view-greybox && python3 build/prototype-why-view.py`, then open `local-data/prototypes/why-view-greybox.html`. Switch variants with the bottom bar, ← / → keys, or `?variant=a|b|c`. Project filter chips in the header (the shared-chrome rider from the what-view).

**Data (real):** all 200 backfill findings (26 days, peak day 2026-07-27 = 44 findings), 27 real `.claude/` commits mined from 9 sibling repos at generation time, and 118 real permission-allowlist rules from the two `settings.local.json` files as the churn class — **churn timing is simulated** (hash-spread over active days, tagged in the UI) because snapshot capture doesn't exist yet. Linking is the real #4 mechanism: deterministic same-project same-day filename-stem match, no model — 3 of 27 mechanical commits link; the rest read "changed, no stated rationale".

**The three variants each embody a candidate noise policy:**
- **A — Interleaved stream:** one chronological history; findings as cards (first quote inline, rest collapsed), mechanical commits as one-liners in place, churn rolled up per day/project. Policy: collapse-by-class, everything visible.
- **B — Two lanes on a date spine:** narrative lane vs mechanical ledger, literal side-by-side; churn dimmed with a "hide permission churn" toggle. Policy: separate + dim + user toggle.
- **C — Day ledger:** the what-view's winning collapsed-row pattern applied to time — one row per day (date · headline · counts · projects), drill in. Policy: default-collapsed everything.

**React to:**
1. The 2026-07-27 day in variant A — 44 full cards. Is the drowning real, and does A survive it at all?
2. 2026-07-31 in variant B — a full mechanical lane against an empty narrative lane (backfill ends 07-30). Is that asymmetry informative or alarming?
3. Evidence anatomy — does the inline-first-quote (A) beat fully-collapsed quotes (B/C)? Noticed on real data: the `why` line often near-duplicates the first quote.
4. Which churn treatment feels right: roll-up (A), dim+toggle (B), or buried-in-day (C)?


---

**comment · 2026-08-03**

## Resolution

**Winner: variant C — the day ledger.** One collapsed row per day (date · headline finding · counts · projects), drill in for detail. At real volume (26 active days, 200 findings, 44-finding peak day) the collapsed rows keep the whole timeline digestible in a single screen; variants A (interleaved stream) and B (two lanes) die with the branch.

**Entry anatomy** (question 1): change headline + why line, verbatim quotes fully collapsed behind a "N quotes · status" summary with exact/fuzzy/unresolved badges; unresolved renders as "quote could not be located (msg N)". Observation for Design: the why line often near-duplicates the first quote on real data.

**Model vs mechanical side by side** (question 2): mechanical entries render as compact one-liners under a "mechanical" subhead inside the day expansion — linked ones point at their finding (⇠), unlinked read "changed, no stated rationale". The #4 linking mechanism (deterministic name+window, no model) linked 3 of 27 real commits; days with mechanical-only activity (e.g. 07-31, past the backfill's findings window) read fine as ledger rows.

**Noise policy** (delegated by #4): default-collapsed day rows carry churn as a count in the row summary, expandable per project inside the day. No dimming, no toggle. Churn timing was simulated (real allowlist rules, hash-spread dates) — real snapshot capture replaces this in the build.

**Additions validated in review:** a per-day stacked chart (findings / mechanical / churn) between the filter chips and the ledger — scrollable calendar-continuous strip, newest at right, spanning the sparse mechanical tail back to May; x-axis time filtering (click a bar for a day, a second for a range, again to deselect, clear to reset); project and time filters compose — chips reshape the chart bars and hide non-matching day rows.

**Riders to the Design-inputs bundle:** the chart + time filtering; filtering confirmed as shared header chrome (project chips + time controls); collapsed-quote evidence anatomy; the why-duplicates-quote observation. Finding categorization: the layout did not demand grouping, so it stays post-v1 per ADR-0002.

Prototype (all three variants + switcher) captured on `prototype/why-view-greybox`; the code is throwaway, this comment is the answer.


