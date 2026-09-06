# #43 Remove the why-pass from analyze.py and the schema

state: closed · labels: wayfinder:task · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Remove the why-pass from `analyze.py` and the schema per the v1 scope ADR, taking the pipeline code and eval burden that existed solely for it. Keep the silent-change backstop capture (renders nowhere in v1). Decide and record whether existing findings rows are dropped or left inert.


---

**comment · 2026-08-25**

## Resolution

Done in commit 8cdf8be. The why-pass is removed end to end; all 64 build tests pass and the live db is migrated.

**Existing findings rows: dropped, not left inert.** The migration in `init_db` drops `findings` (335 rows), `evidence` (566), and `runs` (8), and drops `change_events.finding_id` (0 rows were linked — the linker never fired in production). Rationale: renderer-less tables in a live schema invite confusion, ADR-0006 records the operator choosing the clean cut, and nothing is unrecoverable — the raw why-pass model outputs stay cached on disk (`local-data/backfill/why/`, `local-data/analysis/why-v2/`) and the resolution ladder lives in git history, so the rows could be re-derived without model spend if a future effort wants them.

**Removed:** the why-pass loop and prompts constants in `analyze.py`; `resolve_why_findings` / `valid_why_json` / `link_finding` / `record_run`; the three `why-*` prompt files; the eval regression harness (`eval/resolve.py`, `score.py`, `run.sh`, `corpus.json`, the harness README) — its 97% baseline story survives in git history; the `why` view key in the default config.

**Kept:** the silent-change backstop capture, unchanged (all three sources still tested); `eval/extract.py` as the frozen ADR-0002 extraction contract the what-pass consumes; `what-v1.txt` as the prompt of record for imported history rows.

**Consequential calls, recorded here:**
- The MODEL pin (`claude-haiku-4-5-20251001`) moved from `eval/corpus.json` into `analyze.py` — the ADR-0002 "pin bump via passing regression" path retired with the harness, so a future bump is a plain edit plus the weekly spot-check.
- Root `backfill.py` deleted — mild scope widening: it ran both passes, but it's a completed one-off (ticket #11) hard-dependent on three deleted files, and its outputs remain importable via `import_backfill.py`.
- The backfill importer now checks only the what half for completeness, so sessions the backfill left incomplete solely for a bad why output import as `done` — strictly more history, correct under two-view v1.
- `call_cached` lost its `validate`/`.bad` quarantine path (why-only); what-pass caching behaviour unchanged.

