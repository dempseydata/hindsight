# #50 Review residue from tickets #41-#43: scan crash paths, migration wipe window, doc-truth drift

state: closed · labels: bug, needs-triage · opened: 2026-08-25 · closed: 2026-08-26

Found by the pre-commit review run during ticket #44 (server skeleton). None of it touches #44's diff — all residue in landed work from #41–#43. Ranked:

**Correctness (analyze.py)**
1. `scan_transcript` crashes (TypeError, confirmed by execution) on a non-string `tool_use` name — `re.search(r"\s", name)` at ~430. Violates the counted-never-fatal contract; one bad line aborts the whole run.
2. `_cli_program` crashes (TypeError, confirmed) when a Bash `command` value is a list/dict — passes the truthiness guard, dies in `re.split`. Needs an `isinstance(command, str)` guard.
3. The #42 migration's wipe (in shared `init_db`) and its refill (`fill_substrate`) are split across callers: `import_backfill.py` runs the wipe but never refills. A transcript pruned (cleanupPeriodDays) between wipe and next `run_analysis` loses that session's substrate permanently.
4. Malformed-name skip fires before streamed-duplicate dedup — `skipped_records` over-counts one malformed call once per streamed record.
5. The #43 cut is an **unconditional** `DROP TABLE IF EXISTS runs/findings/evidence` on every `init_db` — a standing destructive startup side effect; also `ALTER TABLE … DROP COLUMN` newly requires SQLite ≥ 3.35. Consider a `PRAGMA user_version` guard for the accreting migration sniffs.

**Doc truth**
6. CONTEXT.md still defines **Run record / `runs` table** — deleted by #43, and per (5) any recreated `runs` table is silently destroyed. Prune the entry.
7. ADR-0002 still mandates the deleted frozen-eval gate for model-pin moves; never amended when ADR-0006 removed the harness. MODEL literal now lives in analyze.py + CONTEXT.md + ADR-0002.
8. design/build-handoff.md still claims the design ADRs "none exist yet" / reasoning "lives nowhere else" — false since #41 wrote ADR-0007/0008.

**Quality (smaller)**
9. `tool_events` rows are 10-slot positional lists mutated by magic index (`ev[3], ev[9]`) mirrored by eye into `fill_substrate`'s column list.
10. `_cli_kind`: hand-rolled `_kind_cache` dict vs `functools.cache`; the unused `which=` param is ignored on cache hits (broken injection seam).
11. No index on the message-lens join columns (`tool_events.message_id` / `usage.message_id`) — the map defers this call to the where-view ticket #48; noting here so it isn't lost.
12. Why-pass residue: `raw_parts`/`zip` materialization, `process_session`'s dead `return None` contract; `eval/extract.py` stranded in retired `eval/` behind a `sys.path.insert(0, …)` that shadows any future top-level `extract` module.



---

**comment · 2026-08-25**

Additions from the pre-commit review run during ticket #45 (what-view). These live in **#44's committed chrome** (`build/serve.py`), so they extend this ledger rather than the #41–#43 list in the body:

**Correctness (serve.py chrome)**
13. Chart range end is `MAX(sessions.date)` — session *start* days — while day buckets key on `usage.at`. A session crossing midnight puts usage rows on a day the render loop never draws and the presets never anchor to: the newest day's tokens silently vanish from chart and window.
14. Empty `sessions` table → `DATA.range = [null, null]` → `applyPreset("14")` throws `RangeError` at load, killing all page JS (chips, chart, view mount). The only startup guard is that the DB *file* exists.
15. A listener-created DB (`listener.py` writes only `otel_events`/`otel_metrics`) passes the file-exists guard, then every GET dies unhandled (`no such table: sessions`) — traceback instead of the intended "run an analysis first".
16. Chip policy degenerates at `total_tok == 0` (`0 >= 0` is true for every project): before the first substrate scan, every non-path project gets a chip and the 1% threshold does nothing.

**Quality (smaller)**
17. `main()`'s hand-rolled `args.pop(0)` flag parser vs the repo's `argparse` convention (`analyze.py`, `import_backfill.py`); usage line dug out of `__doc__.splitlines()[2]` breaks silently if the docstring is reworded; `--port` with no value raises bare `IndexError`.
18. `REPO`/`DEFAULT_DB` re-declared in serve.py rather than imported from `analyze` (which `import_backfill` already does); a DB-path change would silently fork the two.
19. `test_serve.fixture_db` hand-writes DDL that drifts from `analyze.SCHEMA` (already omits `cli_version`/`size`/`skipped_records`); `analyze.init_db` is the fixture pattern the other test modules use.
20. For the #47 floor audit: 9px chart axis labels in `--o-axis` (#6f7794) sit below 4.5:1 on the panel. The equivalent 11–13px text-role violations (`--o-faint` on `.note`/`#ctl`/ledger counts) were fixed to `--o-dim` in the #45 diff; the in-chart treatment is #47's call.



---

**comment · 2026-08-25**

From #47's floor audit (non-floor P2): the header chart's click-a-bar day columns are SVG rects with no keyboard access or ARIA — keyboard users can't reach day/range filtering. Window preset buttons cover the common cases, hence P2. Candidate fix: make each column a focusable element (tabindex + role=button + aria-label with date/tokens, Enter/Space handler) or add a date-range input fallback.


---

**comment · 2026-08-25**

Review residue from #49's pre-commit pass (off-diff, pre-existing): on a DB with zero sessions/usage, the chrome's `DATA.range` is `[null, null]` (`MAX(date)` → NULL), so `applyPreset("14")` → `addDays(null, …)` throws a RangeError and kills all page JS — the page renders with dead chrome instead of an empty state (`build/serve.py` header_data / CHROME_JS, ~L186). Solo-operator DB is never empty today, so cosmetic-tier — but a fresh clone-and-run hits it before first ingest. (A second finding against the #42 migration was refuted: `transcript_path` is `TEXT NOT NULL`, so `Path(None)` cannot occur.)


---

**comment · 2026-08-26**

Closed by 1d8817d. All findings addressed: 1-5 (scan crash paths, dedup-before-malformed, migration wipe+refill unified in init_db, PRAGMA user_version gate on the sniffs), 6-8 (CONTEXT.md Run-record pruned, ADR-0002 amended for the retired frozen-eval gate, build-handoff points at ADR-0007/0008), 9-12 (dict event rows, functools.cache, message-lens indexes, extract.py moved eval/ -> build/ with the sys.path shadowing gone), 13-19 (range end covers midnight-crossing usage, empty/listener-only DB guards, zero-token chip leg, argparse, paths imported from analyze, fixture on real DDL), and the P2 keyboard access (focusable day columns, Enter/Space, aria, focus restore). Finding 20 was already resolved by ticket #47. Verified: 90 tests green plus a browser smoke of empty-DB and real-DB pages (zero console errors; keyboard day-select works).

