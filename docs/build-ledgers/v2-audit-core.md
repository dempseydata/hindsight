# Build ledger: #82 v2 audit core — branch night-shift/v2-audit-core

Authority: push + tracker yes · End state: branch only · Baseline: 255 tests (1 skipped), 30 s

Order: #84 → #85 → #86 → #87 → #88 → #89 → #90 → #91 → #92 → #93 → #94. Human (skipped): #95, #96.
Human-verified (built, left open): #84 (async on Stop/SubagentStop), #91 (real-data equivalence run), #93 (live install, launchd), #94 (local-process.md review, master frontmatter).
Contracts: ADR-0039.

| Ticket | Status | Commit | Rounds | Suite | Notes |
| --- | --- | --- | --- | --- | --- |
| #84 | built, open for human check | 10206e1 | 1 | 261 tests, 31 s | `async` on Stop/SubagentStop needs a live session |
| #85 | closed | 52ceaf5 | 0 | 266 tests, 48 s | |
| #86 | closed | (this commit) | 2 | 274 tests, 55 s | suite at 1.8× baseline |

## Owed
- #91: `size` should be the high-water offset always (ADR-0039 §7), not the file size — deferred from #86.
- #87: the drift guard (ADR-0038 §3) must skip when no session is due, not only when the derivation job raises — deferred from #85.

## Decisions
- #84: raw store columns are `session_id`, `agent_id`, `byte_offset`, `high_water`, `last_hash`, `last_size`; each new table gets a unique index on `ifnull(agent_id,'')` — ADR? yes (permanent once v10 ships; fold into ADR-0039 §8)
- #84: folder identity stored as `transcripts.folder_identity` on the parent registry row; first recorded wins — ADR? no
- #84: a rewritten prefix is breakage condition 6, `source='capture'`, one open row per session; `BREAKAGE_COLS` gains `session_id` — ADR? yes (amends ADR-0033/0037's condition list)
- #84: `provenance` defaults to `'v1'` until #87 — ADR? no
- #84: `otel_histogram` table created in v10 (ADR-0039 §1) — ADR? no
- #84: the capture hook calls `init_db`, so it runs the migration itself — ADR? no
- #84: a payload naming no transcript, or a path not ending `.jsonl`, writes nothing; a missing cwd records no identity; events other than SessionStart/Stop/SubagentStop exit before opening the store — ADR? no
- #85: the lock file is `analysis.lock` beside the db (Hindsight home unless `--db` moves it) — ADR? no
- #85: a migration failure re-raises (exit 1, traceback) and writes no health row; staleness surfaces it — ADR? no
- #85: v1 steps mapped to job slots: sync+redate = sweep; invalidate_grown+fill_substrate = derivation; extract+model loop = what-pass — ADR? no
- #85: backstop and sunk-cost scan are two named jobs; error text `<job>: <ExcType>: <msg>` joined by `; ` — ADR? no
- #86: deriver state keyed `<deriver>@<version>` (`records_index@1`); a version bump finds no state and rebuilds — ADR? no
- #86: a line that parses but is not a JSON object is also condition 5 (`source='derivation'`, `derivers='records_index'`) — ADR? no
- #86: session rows are created only for parent registry rows with high_water > 0; exclusion and cli_version read from the stored head; `size` is the file size, or the high-water if the file is gone — ADR? no
- #86: registry sync moved into project bookkeeping (the sweep slot), amending #85's mapping — ADR? no
- #86: the day expression is `analyze.session_day()`, read by both views, the drift guard's since, and `attribute` — ADR? no
- #86: derivation runs the records index first, then the v1 substrate scan, each regardless of the other; the sweep fails per file (OSError) and skips non-files; v1 scan reads with `errors="replace"` — ADR? no
- #86: fresh schema no longer creates `audit.date` — ADR? no

## Blocked

## Nits
- #84: acknowledging a condition-6 row does not stick; the next firing reopens it. The banner's "acknowledge … to close" overpromises until a reset path exists.
- #84: the condition-6 banner keeps the heading "transcript shape changed" (`cli/serve.py:150`).
- #84: `_migrate_v10` commits `user_version=10` before `VACUUM`; if that VACUUM fails, `auto_vacuum` is never retried.
- #84: a refused rewrite still records capture health as a success.
- #84: `docs/` (flows, architecture, cron, permissions, variables) still describes `hook.py` — re-run `/document-app` after the shift.
- #85: the narrative still runs when the what-pass raises.
- #85: `error_text` is kept after a success (only `failing_since` clears).
- #86: excluded sessions are still captured and indexed (the spec allows it).
- #86: condition-5 rows send no notification.
- #86: `docs/flows.md` and `docs/automation.md` still describe `redate_sessions` and `audit.date`.
