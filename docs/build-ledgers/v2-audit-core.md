# Build ledger: #82 v2 audit core — branch night-shift/v2-audit-core

Authority: push + tracker yes · End state: branch only · Baseline: 255 tests (1 skipped), 30 s

Order: #84 → #85 → #86 → #87 → #88 → #89 → #90 → #91 → #92 → #93 → #94. Human (skipped): #95, #96.
Human-verified (built, left open): #84 (async on Stop/SubagentStop), #91 (real-data equivalence run), #93 (live install, launchd), #94 (local-process.md review, master frontmatter).
Contracts: ADR-0039.

| Ticket | Status | Commit | Rounds | Suite | Notes |
| --- | --- | --- | --- | --- | --- |
| #84 | built, open for human check | 10206e1 | 1 | 261 tests, 31 s | `async` on Stop/SubagentStop needs a live session |
| #85 | closed | 52ceaf5 | 0 | 266 tests, 48 s | |
| #86 | closed | fdfc635 | 2 | 274 tests, 55 s | suite at 1.8× baseline |
| #91 | built, open for human run | 29ff02f | 0 | 277 tests, 54 s | real-data equivalence: `eval/extract_equivalence.py` |
| #87 | closed | (this commit) | 1+3 | 283 tests, 52 s | blocked once; v1 rows replaced per captured agent (ADR-0039 §9) |

## Owed

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
- #87: operator decided v1 rows are replaced only for agents the raw store holds — ADR? yes (ADR-0039 §9, done)
- #91: the first v2 run holds every swept session one run (records captured by the run's own sweep count as just captured; #79 §3) — ADR? no
- #91: the live guard reads all of a session's raw records, subagents included — ADR? no
- #91: raw records reach the unchanged `extract.py` through `/dev/stdin` (macOS/Linux only) — ADR? no
- #91: growth compares against the high-water; the substrate is wiped only when the file is on disk; sessions with no registry row are skipped — ADR? no
- #87: condition 3 retired with the v1 scan; `scan_runs` left for #88's v12 to drop — ADR? no
- #87: substrate derivers write nothing for sessions with no `sessions` row; a captured, unexcluded parent (high_water > 0) with no row yet raises `NotSynced` and the session stays due — ADR? no
- #87: v3/v8/v9 rescan migrations no longer rescan; the derivers do — ADR? no
- #87: subagent counts read the transcript registry plus the frozen `subagent_transcripts` table — ADR? no
- #87: the 300 s live guard on derivation is retired (ADR-0031 §6, spec "Derivation has no guard") — ADR? no

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
- #91: `sessions.size` is not lowered to the high-water when a v1 row's size exceeds it (kept deliberately: lowering would trigger spurious re-audits as capture catches up).
- #91: `held_live` treats an unparseable `captured_at` as not live.
- #87: with the parent captured and a subagent not, the histogram keeps v1 rows and adds the parent's raw rows (the parent counts twice in the histogram); ADR-0039 §9 allows it, but its "avoids double counting" sentence overstates.
- #87: `skipped_records` now counts only captured agents.
- #87: each session is parsed once per deriver (four times).
- #87: a DriftTest monkeypatches `analyze.derive` (no fixture path to a mid-run capture).
- #87: the drift guard's skip is silent (spec story 36 gives no form).
- #87: `docs/` still describes `fill_substrate` and `_reset_scanned`.
