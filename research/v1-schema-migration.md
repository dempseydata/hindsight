# Refactor or rewrite: can record-level ingest migrate into the v1 schema?

**Ticket:** [#66](https://github.com/dempseydata/hindsight/issues/66) (part of map #59) · **Date:** 2026-11-13 · **Method:** a read of the v1 schema and every module under `build/` at `6918c49`, a grep of every SQL reader per table, and counts from the live database (`local-data/hindsight.db`, opened `mode=ro`, `PRAGMA user_version = 9`, 450 MB). Transcript survival was tested by checking each `sessions.transcript_path` on disk and searching `~/.claude/projects/*/*.jsonl` for the session id.

## Answer

**It migrates. Route A, a schema bump to `user_version = 10` plus new capture and derivation modules on the existing database and codebase, is the cheaper and safer route.** v1 already has the mechanism ADR-0031 needs. `init_db` gates one-shot migrations on `PRAGMA user_version` and has done so nine times. `_reset_scanned` plus `fill_substrate` is a wipe-and-refill that already leaves a vanished transcript's rows untouched, which is the `v1`-provenance rule under another name. The parsing logic in `substrate.scan_transcript` and `extract.msg_texts` survives intact once its input changes from a file path to an iterable of raw lines.

A rewrite (Route B) would rebuild about 3,400 lines of application code and 4,200 lines of tests, and it would still need an ETL from the v1 database. That ETL is the Route A migration, run across two files rather than one. Most of the history it must carry cannot be regenerated.

**Correction to the ADR-0031 consequences and the #65 resolution.** The frozen `v1` set is not "about 150 sessions". 400 of the 486 synced sessions (82%) have no transcript on disk. They date from 2026-06-26 to 2026-10-26 and hold 366 of the 433 audit rows, 41,796 of 51,528 `tool_events`, 37,394 of 45,848 `usage` rows and 33,024 of 50,941 `field_histogram` rows. The figure 157 is the subset never substrate-scanned. `v1` provenance is the majority of history, so whichever route is taken must carry it intact.

## v1 tables

Row counts are from the live database. "Readers" lists the modules that select from the table, excluding tests.

| Table | Rows | Fate under the record-level model | Readers |
| --- | ---: | --- | --- |
| `sessions` | 486 | **Keep, columns change.** `id`, `project`, `folder_identity`, `attribution_source`, `status`, `audited_size` stay. `transcript_path` stays as capture's locator. `size` and `skipped_records` (the scanned marker) are replaced by capture and deriver high-waters. `cli_version` moves to the records index. `date` stops being stored for `raw` sessions (ADR-0031 §5) but **must stay for the 400 `v1` sessions**, which have no records to take a timestamp from. | `analyze` (26 sites), `serve` (`what_data`, `header_data`, `synced_through`, `where_data`, `declaring_projects`), `how` (`_events`, `how_data`), `substrate` (`fill_substrate`, `adr_count`, `former_names`), `import_backfill` |
| `audit` | 433 | **Keep as-is,** add provenance. This is model output, not a mechanical derivation. 366 rows have no transcript left and are frozen. The rest can be regenerated, but only at a model call each. `audit.date` duplicates `sessions.date` and goes with it. | `analyze` (`insert_results`, `process_session`, `redate_sessions`), `serve.what_data`, `how.how_data`, `substrate.fill_substrate` (stamps `adr_count`) |
| `tool_events` | 51,528 | **Derived table** (substrate deriver), provenance `raw` or `v1`. 41,796 rows are `v1`. | `serve.where_data`, `how._events`, `substrate.adr_count`, `analyze` (wipe sites) |
| `usage` | 45,848 | **Derived table** (substrate deriver). 37,394 rows are `v1`. | `serve` (`header_data`, `what_data`, `where_data`, `synced_through`), `analyze` (wipe sites) |
| `command_grains` | 498 | **Derived table** (substrate deriver). 396 rows are `v1`. | `how._events`, `analyze` (wipe sites) |
| `field_histogram` | 50,941 | **Derived table** (drift-guard deriver, rebuilt on the raw store, an open map item). 33,024 rows are `v1`. | `analyze` (`version_histogram`, `check_drift`) |
| `subagent_transcripts` | 753 | **Dropped as a growth watermark.** Capture's per-(session, agent) high-water replaces `size`. The subagent count `serve.subagent_counts` reads becomes a count of distinct agent ids in the raw store, or over `v1` rows for frozen sessions. 600 rows belong to sessions with no transcript left, so keep the table frozen for those rather than deleting it. | `serve.subagent_counts`, `analyze` (`_subagents_grew`, wipe sites) |
| `scan_runs` | 44 | **Keep.** It is drift-guard state, condition 3's baseline. Its meaning moves from "per analysis run" to "per derivation pass". | `analyze.check_drift` |
| `breakage` | 11 | **Keep as-is.** A capture rewrite (ADR-0031 §2) becomes a new condition on it. | `analyze`, `serve.breakage_banner`, `menubar.open_breakages` |
| `excluded_sessions` | 1,472 | **Keep as-is.** Capture must consult it too, because hindsight's own `claude -p` calls fire hooks. | `analyze` (`sync_sessions`), `serve.where_data` |
| `status_narrative` | 6 | **Keep as-is.** It invalidates itself by `ledger_hash`. | `analyze.refresh_narratives`, `how.narrative` |
| `project_presence` | 42 | **Keep as-is** (ADR-0018). | `analyze` (presence, canonicalisation), `serve.hidden_projects`, `substrate.former_names` |
| `blobs`, `backstop_state`, `change_events` | 331 / 21 / 580 | **Keep as-is.** The backstop does not read transcripts. | `analyze` (backstop) |
| `sunk_cost` | 173 | **Keep as-is.** | `sunk_cost`, `serve.where_data` |
| `otel_events`, `otel_metrics` | 306,294 / 64,580 | **Keep as-is.** They make up 413 MB of the 450 MB file, with the index. | `listener` (writes), `serve.where_data`, `analyze.hook_folder_identity` |

**New in v10:** `raw_records` (key, compressed bytes, `captured_at`), a capture high-water per (session, agent) with the last record's hash, and one version plus high-water row per deriver. The records index is the first deriver. Add a `provenance` column to `tool_events`, `usage`, `command_grains`, `field_histogram` and `audit`. Expect about 189 MB more on top of today's 450 MB (ADR-0031).

## v1 modules

| Module | Lines | Fate |
| --- | ---: | --- |
| `substrate.py` | 409 | **Adapts, small change.** `scan_transcript(path)` opens a file and iterates lines. Make it take an iterable of lines, and its 31 tests keep their meaning. `classify`, `tally_record`, `adr_count`, `former_names` and `FIELD_CONTRACT` survive. `fill_substrate` reads from the raw store and writes provenance `raw`. `subagent_transcripts()` (file discovery) moves to capture. **The real cost is incrementality.** The scan pairs `tool_use` with `tool_result` across records and deduplicates usage by message id, last record wins. "Work forward from the high-water" (ADR-0031 §6) therefore needs either a per-session rederive, the session's records being small, or carried state for unpaired calls. A per-session rederive on growth is what v1 does today. |
| `extract.py` | 87 | **Adapts.** `msg_texts` survives. `main` reads lines from the raw store instead of a path. It runs as a subprocess on a path today (`analyze.extract_session`), so either import it or write the session's lines to a temporary file. |
| `analyze.py` | 1,717 | **Adapts, most of the change lands here.** `init_db` gains v10. `sync_sessions` (a glob over `~/.claude/projects`) gives way to capture-driven discovery. `head_scan` and `redate_sessions` give way to the records index. `invalidate_grown` and `_subagents_grew` (size watermarks) give way to high-water comparison. `check_drift` is rebuilt on the raw store. Everything after the substrate survives: `classify_and_extract`, `process_session`, `refresh_narratives`, the backstop, presence, canonicalisation, attribution, `acknowledge-breakage` and the nightly. `DEFAULT_DB` moves to `~/.hindsight/` (#60). |
| `hook.py` | 123 | **Adapts.** `Stop` and `SubagentStop` trigger capture from `transcript_path` / `agent_transcript_path` (#61). Whether the hook writes itself or posts to the listener is a design question, given ADR-0001's single writer. |
| `listener.py` | 289 | **Survives.** It may gain a capture endpoint if capture goes through it. The DB path constant moves. |
| `serve.py` | 886 | **Survives.** It needs adapting only where it reads `sessions.date` (`what_data`, `synced_through`) and `subagent_transcripts`. A view that coalesces the records-index span with the frozen `v1` date keeps the change to a join. |
| `how.py` | 403 | **Survives.** One `sessions.date` read in `how_data`. The ADR-0032 resolution change in `read_declaration` is orthogonal to this ticket. |
| `sunk_cost.py`, `menubar.py` | 267 / 201 | **Survive.** `menubar` has a DB path constant. |
| `import_backfill.py` | 113 | **Dies.** It is the one-shot import from ticket #20. Its rows are already in the database, it has nothing to import under v2, and its 6 tests go with it. |

## The two routes

### Route A: schema bump and new modules

**What breaks.** The size-watermark tests (`invalidate_grown`, `_subagents_grew`, and the growth and top-up cases in `test_analyze`), the `head_scan`/`redate` tests, and tests that assert on `sessions.size` or `skipped_records` as the scanned marker. The test seam itself survives. `test_helpers.write_transcript` followed by `run_analysis` still works if `run_analysis` captures before it derives, so most of the 83 + 58 + 26 tests in `test_analyze`, `test_serve` and `test_how` pass unchanged.

**Cost.** Two new modules (capture and the deriver framework with the records index). One v10 block in `init_db`. Edits to about 8 functions in `analyze.py`, 2 in `substrate.py`, `extract.main`, 3 reader sites in `serve.py` and `how.py`, and `hook.py`. Roughly 20 to 30 tests rewritten, plus new tests for capture and the derivers.

**Risks.**
- *Migrating a live 450 MB file.* The listener writes under WAL all the time. The v10 backfill captures about 451 MB of transcripts (about 189 MB stored) and must commit per session, as `fill_substrate` already does, not in one transaction. Take an `sqlite3 .backup` copy first. The DDL is additive (`CREATE TABLE`, `ALTER ADD COLUMN`). The one-shot `UPDATE ... SET provenance='v1'` covers rows whose transcript is gone at migration time, which is exactly `_reset_scanned`'s existing test, `Path(path).exists()`.
- *Rows without raw bytes.* Frozen by design: 400 sessions. A deriver bump must delete `WHERE provenance='raw'` only, never by session or by table. This is the same discipline as `SUBSTRATE_TABLES` today, where forgetting one table duplicates its rows. Pin it with one test per derived table.
- *The stored date.* ADR-0031 §5 says no stored session date, but `v1` sessions have no other date. Keep `sessions.date` populated for `v1` rows only, or record it as an amendment to §5.
- *Move to `~/.hindsight/` (#60).* This is a file move plus four path constants and the launchd plists, under either route. Moving the same file carries everything.

### Route B: rewrite with a fresh schema and database

**What breaks.** Everything that reads the database. `serve.py` (886 lines, 58 tests), `how.py` (403, 26), `analyze.py` (1,717, 83) and `substrate.py` (409, 31) are rewritten or ported against the new schema. That is about 3,400 lines of application code and about 4,200 lines of tests.

**Cost.** The above, plus an ETL from the v1 file. Carrying history is not optional (ADR-0018, and the map's "v2 is built in this repository"), so the ETL must move `sessions`, `audit`, the four substrate tables, `project_presence`, `breakage`, the backstop tables, and either the 413 MB of OTel tables or a decision to drop them. That is the Route A migration with a second file and a schema translation added.

**Risks.**
- *Irreproducible data lost in translation.* 366 audit entries have no transcript. 114 `operator` attributions are hand stamps that exist only in this database. The presence history behind every former name (ADR-0018) exists nowhere else. A translation bug loses these silently and permanently, whereas Route A leaves them in place.
- *Rebuilt behaviour drifting.* v1's rules are pinned by its tests: lost status (ADR-0015), live guard and top-up (ADR-0013), subagent filing (ADR-0019), error text (ADR-0027), the drift guard (ADR-0020), local-day buckets (ADR-0014). A port has to re-earn every one.
- *The only gain.* A clean schema without dead columns. Route A can get most of that later with one `DROP COLUMN` migration once the views no longer read them.

## Recommendation

**Route A.** The record-level model adds a layer under v1's derived tables without replacing them. Of the eighteen v1 tables, eleven are kept as-is and two (`sessions`, `audit`) are kept with column changes. Four become derived tables that keep their shape and gain a provenance column. One (`subagent_transcripts`) is retired as a watermark. No v1 table's meaning is contradicted. v1 already provides the migration gate, the per-session commit and the frozen-if-vanished rule.

A rewrite pays about 7,600 lines of code and tests to reach the same schema, and it puts the 82% of history that cannot be regenerated through a translation step. Two items need a decision before `to-spec`:

1. Incremental derivation versus a per-session rederive for the substrate deriver, given cross-record pairing.
2. Whether ADR-0031 §5 is amended to keep `sessions.date` for `v1` rows.

## Sources

- Schema and migration gate: `build/analyze.py` `SCHEMA`, `init_db` (v1 to v9), `_reset_scanned`, `_migrate`, `SUBSTRATE_TABLES`. OTel schema: `build/listener.py` `SCHEMA`.
- Capture-adjacent code: `build/substrate.py` (`scan_transcript`, `fill_substrate`, `subagent_transcripts`, `_is_live`), `build/analyze.py` (`sync_sessions`, `head_scan`, `redate_sessions`, `invalidate_grown`, `_subagents_grew`, `run_analysis`), `build/extract.py`, `build/hook.py`.
- Readers: `build/serve.py` (`what_data`, `header_data`, `where_data`, `synced_through`, `subagent_counts`, `hidden_projects`, `breakage_banner`), `build/how.py` (`_events`, `how_data`, `narrative`), `build/menubar.py` (`open_breakages`).
- Decisions: ADR-0031 (the model), ADR-0013, ADR-0014, ADR-0015, ADR-0018, ADR-0019, ADR-0020, ADR-0027. Tickets #60 (DB location), #61 (hook payloads), #65 (the model).
- Database: `local-data/hindsight.db`, read-only, as of the 2026-11-13 run. Counts only. Sizes from `dbstat`.
