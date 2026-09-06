# #70 Session-opener noise in off-script: ignore list in the declaration, or a view-side drop

state: closed · labels: wayfinder:grilling · opened: 2026-08-29 · closed: 2026-08-29

## Question

`/clear` and `wayfinder` open sessions rather than mark process steps, and together they are ~85 of hindsight's 138 off-script events, burying the list that exists to show real deviation. #65 left them visible. Decide: an `ignore:` key in the process declaration (an ADR-0011 schema change, authored per project, honest because it is declared), a fixed view-side drop of session boundaries (simpler, but hides), or leave as is. Whatever is chosen, the off-script total must still say what was excluded.


---

**comment · 2026-08-29**

## Resolution

**View-side fixed drop, exclusion stated in the total.** No `ignore:` key — ADR-0011 amended (ticket #70), CONTEXT.md gains *Session boundary*. Landed in 9c5bb16.

**Why not the declaration.** The ticket framed `ignore:` as "honest because it is declared" and the view-side drop as "hides". Once the total states the exclusion, both are equally honest, and what remains is ownership: `/clear` and `/model` are Claude Code's, `wayfinder` as session front door is a house-pipeline convention — none is a project's process. Declaring them in every `my-process.md` repeats a platform fact four times, and any project that forgets gets the buried list back.

**Mechanics.** `SESSION_BOUNDARIES = ("clear", "model", "wayfinder")` in `build/how.py`, matched by the same name rule as markers, applied **only to events no stage claimed** — a declaration that lists `wayfinder` under a stage still wins (thisisme today; the test covers it). `how_data` returns `boundaries: {name: count}` beside `off_script`; the heading reads e.g. *Off-script · 50 events · 36 distinct · 88 session-boundary events excluded (/clear ×51, /mattpocock-skills:wayfinder ×36, /model ×1)*.

**Real data.** hindsight off-script 138 → 50 (the residue is writes to `eval/`, `my-process.md`, `backfill.py`, `CLAUDE.md`, and `skill design` ×2 — the deviation the list exists to show); thisisme 16 → 8.

Extend the set only when a new opener is observed dominating the list, never speculatively.


