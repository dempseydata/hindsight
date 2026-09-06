# #64 Greybox the how-view: rendering mechanics with real data

state: closed · labels: wayfinder:prototype · opened: 2026-08-26 · closed: 2026-08-28

## Question

The rendering mechanics ADR-0010 explicitly deferred to greybox with real data — settled by reacting to a throwaway prototype fed from the real trail pipeline:

- Lanes vs a single interleaved column; how stage-anchored bucketing reads when stages interleave heavily (the back-and-forth *is* the texture — does it survive at real density?).
- Granularity and zoom: per-event, per-session, per-day roll-ups — what makes months of history reviewable.
- How the stated-process panel sits beside the trail (the juxtaposition), and the degraded no-declaration rendering.
- Nav entry and relationship to the shared chrome: /what and /where are cross-project with chip filtering; /how is per-project — how the project choice is made and whether the chrome's day-chart/chips participate at all.

Throwaway means throwaway: Impeccable hooks **off** for this ticket, the greybox code dies, and the answers are captured in the resolution comment as the design input for the styled build. Real hindsight data throughout.



---

**comment · 2026-08-28**

## Resolution

Five iterations on real hindsight data (329 events / 83 sessions), plus thisisme (sparse), career-ops (no declaration) and hindsight with its declaration deliberately mangled. The first cut — a stage-tagged chronology, in a single column or in stage lanes, with event/session/day zoom — was rejected on sight: neither reads as "how did I get here". What survived:

**The trail is phase runs, not a chronology.** A run is a band of consecutive trail events sharing one stage; runs shorter than three events fold into the run before them (event-run grain — session-dominant grain was tried and hides thin stages). Off-script events are excluded from segmentation. Runs render **newest first**, each with: stage (colour-keyed to the stated-process panel), date or start → end, session and event counts, the **audit titles of its sessions as the summary**, the commands/skills used, and minor-stage counts ("also: Plan 4 · Design 1"). A session straddling runs is titled only in the run holding most of its events. On hindsight this yields 10 runs; Plan↔Build alternation is the visible texture. Design never forms a majority run — it happened inside Plan sessions — which the view states rather than glosses.

**A status card above the runs — and it is model-written.** Mechanical status (current run + per-run first → last title) duplicated the bands and answered nothing; a paragraph read as narration. The shape that held is a **fact list in three fixed groups: Built / Reversed / Now**, each line dated and traceable to ledger entries, over a mechanical one-liner (current stage since-date, run tally, span). This reopens ADR-0010's "no model narrative" for exactly this artefact — **ADR-0012** records it: input is the run ledger only, output the three-group list, full Evaluation discipline (frozen set and threshold before the prompt), stored and write-gated like an audit, generated after sync on ledger change, degrading to the mechanical line when absent. ADR-0010 carries the amendment; CONTEXT gains *phase run*, *run ledger*, *status narrative*.

**Stated-process panel** (left, 260px): one card per declared stage with count, first → last seen and its markers; "nothing observed" as a dashed card; off-script total with the distinct list collapsed. Kept as-is from iteration 1 — the operator liked it unchanged.

**Degraded states**: absent → dashed banner "No process declaration" with the fix, runs rendered as one unbucketed lane; invalid → banner with the parser's line-numbered reason and the file path. Both keep the full trail. Nothing hides.

**Nav / chrome**: `/how` takes a **project selector, not the chip row** (chips filter on the sibling views; here the choice switches), and the shared day-chart/window chrome does not appear — token-time filtering answers where/what questions, not this one.

**Left to the styled build** (recorded, not decided here): remove `wayfinder` from the Plan markers — it opens every ticket session and colours Build sessions Plan; `/clear` dominates off-script (48 of 102) and wants either an ignore list in the declaration (ADR-0011 change) or a view-side drop; the ≥3 fold threshold is a heuristic to re-judge with styled density.

**Primary source:** the prototype (five iterations) lives on the throwaway branch `prototype/how-view-greybox` (throwaway branch in the private working repo — not exported) (`build/prototype-how-view.py`, fed by `build/how.py`); master keeps this verdict plus ADR-0012 / ADR-0010 amendment / CONTEXT (7930379).



---

**comment · 2026-08-29**

**Addendum (operator, 2026-08-28):** a project with no `my-process.md` declaration is not shown in the how-view — the selector lists declaring projects only. This narrows ADR-0010's "nothing hides" (amendment recorded on the ADR and in CONTEXT). The **invalid** state is unchanged: trail + line-numbered error, so a mangled fence is never mistaken for none.

