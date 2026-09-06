# #17 Analysis-run walking skeleton: session sync + what-pass audit ledger

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-16

## Parent

#15

## What to build

The on-demand analysis entrypoint, end to end for the what-pass: sync sessions from the transcript archive into the `sessions` table (hindsight's own analysis runs excluded by prompt signature, built in), extract per ADR-0002 (indexed pieces, sidecar uuid map, 180K chunk cap), run the frozen what-pass via `claude -p`, and fill the cross-project `audit` table — one row per session with project, date, skip flag, entry markdown, prompt version, model (ADR-0004). Multi-part sessions get the merge call. Model outputs cached on disk; invalid outputs retried next run; subscription-limit exhaustion pauses the run cleanly and the next run resumes (ADR-0003). The frozen prompts move from the eval/ideation trees into their product home with a version identifier. A minimal operator config file starts here: listener port, per-view project include/exclude, default time windows.

## Acceptance criteria

- [ ] Running the entrypoint over a fixture transcript directory produces sessions and audit rows; a second run is a no-op (idempotent)
- [ ] Analysis-run transcripts in the fixture are excluded from the inventory
- [ ] A trivial fixture session stores skip=true with no markdown; a multi-part session stores exactly one merged entry
- [ ] Stubbed model runner failing mid-run leaves remaining sessions pending; the next run completes them (limit pause/resume)
- [ ] Audit rows carry prompt version and model
- [ ] Seam-2 tests use a stubbed model runner only — no live model calls
- [ ] Zero pip dependencies

## Blocked by

- None — can start immediately.


---

**comment · 2026-08-16**

Implemented in 3a1557d: build/analyze.py (analysis-run entrypoint), build/prompts/what-v1.txt + merge-v1.txt (frozen what-pass moved to its product home), build/test_analyze.py (14 seam-2 tests, stubbed model runner only). All acceptance criteria verified — idempotent runs, self-exclusion, SKIP/no-markdown, multi-part merge, limit pause/resume, prompt_version+model on audit rows, zero pip deps. Full build/ suite (22 tests) green.

