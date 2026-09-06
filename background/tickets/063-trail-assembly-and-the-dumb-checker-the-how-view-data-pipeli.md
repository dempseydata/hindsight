# #63 Trail assembly and the dumb checker: the how-view data pipeline

state: closed · labels: wayfinder:task · opened: 2026-08-26 · closed: 2026-08-27

## Question

The how-view's data pipeline, per ADR-0010 — everything below the rendering:

- **Trail assembly**: per workspace folder, the mechanical date-ordered merge of command grains + skill invocations + phase-folder writes, with audit titles supplying the prose. Includes settling where phase-folder writes come from — derivable from existing tool-event rows, or needing capture work (an implementation question, answered here against the real DB).
- **Declaration parsing**: read a project's `my-process.md` frontmatter per the schema ADR; a missing or invalid declaration yields "no declaration", never an error surface.
- **The dumb checker**: presence per stage ("design: nothing observed"), first/last-seen per stage, off-script list (events mapping to no declared stage — the declaration's rot detector). Explicitly no order rules, no conformance verdicts.

Output shape should anticipate the greybox ticket consuming it directly (real data, per-project). Tested per `tdd`; hindsight's own declaration (from the authoring ticket) is the live fixture.



---

**comment · 2026-08-27**

Matcher notes from authoring the declarations (#62): (1) stored grains carry the leading slash verbatim (`/design-sync`, `/mattpocock-skills:wayfinder`) — strip it before ADR-0011's tail-segment comparison, or bare `design-sync` never matches; (2) ADR-0011 is silent on nested path subtrees across stages (`build/` vs `build/docs/adr/`) — decide longest-prefix-wins or treat as invalid, and record it in the ADR.


---

**comment · 2026-08-27**

## Resolution

Landed in 1b7fb40: `build/how.py` + `build/test_how.py` (17 tests; suite 111 green). `how_data(conn, project) -> {declaration, trail, summary, off_script, sessions}` is the shape the greybox ticket consumes — documented in the module docstring.

**Phase-folder writes need no capture work.** `tool_events.file_path` is absolute and workspace projects live at `~/Documents/Claude/<project>/`, so writes are a prefix match on the project root, relativised, then bucketed by declared `paths`. Skill names likewise already exist — `tool_events.consumer` holds the Skill tool's `skill` argument since #42, so ADR-0011's "skill markers inert until extracted" consequence was stale (now noted in the ADR).

**Real-data check (hindsight, 321 trail events):** Ideate 19 (Jul 15 → Aug 1), Design 9 (Aug 3 → Aug 26), Plan 86 (Aug 1 → Aug 27), Build 107 (Aug 3 → Aug 27), Release 1 (Aug 17 — the graphify run). That is ADR-0010's chronology reproduced from the DB alone, with prototype-first showing as Design interleaved through Build. thisisme: valid, 48 events; project-template: valid, 0 events; career-ops: absent → raw trail of 362.

**Decisions made here, recorded as an amendments section in ADR-0011:**
- `commands` and `skills` are one name pool matched against both capture paths. Real data forced it: `implement`, `to-tickets`, `ponytail-review`, `red-team-prd` were declared as commands but invoked through the Skill tool and landed off-script. The cross-stage duplicate check uses `match_name` itself (bare vs qualified forms collide); the same name in one stage's commands *and* skills is not ambiguous — hindsight's own `code-review` does exactly that.
- Leading `/` on stored grains stripped before matching (#62 friction 1).
- Nested path subtrees across stages: longest prefix wins (#62 friction 2).
- Also invalid: a marker key given twice in one stage; `#` comment lines inside the fence. Every invalidity names its line; an unreadable-but-present file is invalid ("cannot read"), never absent.

**Pipeline-shape calls the view inherits:**
- One write event per (session, file) — the first touch. Forty edits to serve.py in one session are one step on the trail.
- All writes under the project root feed the trail, not only "phase folders" — a raw trail must exist without a declaration, and phase folders are only defined *by* one. Consequence: hindsight's off-script list carries 43 writes (`LICENSE`, `.gitignore`, `hooks/*`, `eval/*`, `.claude/*`) plus `/clear` ×48, `/model`, and five stray skills. Whether the view hides housekeeping commands or collapses off-script writes is the greybox's presentation call, as #62 already deferred.

**For #64 (greybox):** `python3 build/how.py [project]` prints summary + off-script for any project; the declaration's `stages` list is the stated-process panel in stated order.


