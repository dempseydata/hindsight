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
| #87 | closed | 3fe14c1 | 1+3 | 283 tests, 52 s | blocked once; v1 rows replaced per captured agent (ADR-0039 §9) |
| #88 | closed | 8112338 | 1 | 288 tests, 56 s | v12 drops `scan_runs` |
| #89 | closed | dd5fb93 | 1 | 294 tests, 56 s | |
| #90 | closed | 16701b1 | 1 | 298 tests, 55 s | where-view wording: optional human look |
| #92 | closed | de496fa | 2 | 305 tests, 61 s | suite at 2× baseline — next implementer moves tests to cheaper seams |
| #93 | built, open for human run | 6336548 | 1 | 320 tests, 39 s | tests moved to cheaper seams (61 → 39 s); live install, launchd, ~100 ms budget need a human |
| #94 | built, open for review | 09924f0 | 1 | 326 tests, 36 s | draft `local-process.md` for review; house master frontmatter edit is the operator's |

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
- #88: the listener stores `service.name` and `service.version` on each OTel event (record attributes win a clash; older events fall in the '' version) — a running listener needs a restart — ADR? yes (changes what the listener stores; ADR-0037 §4 implies it)
- #88: OTel breakage rows: `source='otel'`, versions "<service> <version>", key "<event>.<attr>", baseline per service — ADR? yes (row format persists, the baseline parses it)
- #88: `OTEL_DECLARED` holds the latency and reliability panels' pairs; #89/#90 add theirs — ADR? no
- #88: OTel arrivals do not hold the guard; an OTel histogram version bump rebuilds every session — ADR? no
- #89: gap = (transcript − OTel) / OTel; each day compares only sessions with both transcript usage and non-side OTel `api_request` events that day; the 50-request floor counts those shared requests — ADR? no
- #89: a day with any condition-4 row, open or acknowledged, is never checked again; row `source='cross-check'`, key 'input-side tokens', signed gap in `new_share` — ADR? no
- #89: separate "cross-check" job in the guard slot with the same any_due skip — ADR? no
- #89: breakage banner headings per condition: 4 "input-side tokens disagree", 6 "transcript rewritten", others "transcript shape changed" — ADR? no
- #90: the token source is chosen at render time (no column): OTel `api_request` tokens for a session OTel saw (≥1 api_request), else transcript usage, labelled by usage provenance — ADR? no
- #90: the message lens stays on transcript usage (OTel has no message_id); the measured median skips OTel side requests; OTel subagent tokens come from `agent_id` (CLI ≥ 2.1.310) — ADR? no
- #92: limit env `HINDSIGHT_RAW_DAYS` (0 = never; tests pin 0); a limit overflowing the date maths means never — ADR? no
- #92: health detail JSON `{"raw_days","held"}`; a bad value writes null to both — ADR? no
- #92: newest record from records-index timestamps; a session with none is kept; only `raw` rows become `compacted`; v1 stays v1 — ADR? no
- #92: held: every pending/partial session ("trivial excepted" has no mechanical state), and any session with an open condition-5 or condition-6 breakage — ADR? no
- #92: a compacted session is never re-audited (its audit entry is the lasting output); a resumed tail derives as raw beside compacted rows — ADR? yes (ADR-0034 §5 covers re-capture only)
- #92: compaction clears the session's raw-rowid deriver_state in the same transaction (raw_records rowids are reused after deletion) — ADR? yes (a standing invariant on ADR-0039 §2's rowid table)
- #93: staleness compares another session's newest OTel Stop with capture's newest `captured_at`, with a 120 s grace; compacted sessions skipped; "how long" counts from the first missed Stop — ADR? no
- #93: health lines prefixed "hindsight: ", joined by "; "; an unexpected exception prints "health check failed: …"; exit is always 0 — ADR? no
- #93: SessionStart health entry is synchronous with timeout 5; launchctl calls time out at 1 s; launchd labels and `domain()` moved to `cli/home.py` — ADR? no
- #93: no analysis-staleness rule (no source names a threshold; ADR-0033 rejects a fixed age), so a migration failure (no health row, #85) is not surfaced at SessionStart — ADR? yes (operator decision: is a stale analysis row worth a line?)
- #94: hindsight's `local-process.md` sits at the repo root (tracked); Build paths `build/, cli/, skills/, eval/` so pre-plugin work still buckets — ADR? no
- #98 (2026-11-19): superseded. The draft was dropped (2304326) once the master took hindsight's paths; hindsight resolves from the house master (ADR-0032 amended).
- #94: a relative pointer is read from the CLAUDE.md's folder; the `## Process` section ends at the next `#`/`##` heading; `source` is `local-process.md` or `house master <path>`; the selector lists every project not `absent` — ADR? no
- handover security fix: the what-pass `claude -p` runs with `--tools "" --strict-mcp-config` from a fixed empty temp folder, not the repo; drops the project CLAUDE.md from the model's context; what-eval re-run through the new call, 20/20 ACCEPT (what-v3, Haiku 4.5) — ADR? no

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
- #88: a sharp shift in status mix (an optional OTel attribute 95% → 40%) trips a problem row; transcript keys share the exposure.
- #88: sessions excluded from analysis still feed the OTel histogram.
- #89: a day whose OTel tokens are all zero against non-zero transcript tokens is skipped silently (a zeroed attribute is not caught; a renamed one is, by OTEL_DECLARED).
- #89: a listener outage partway through one session's day can still trip (ADR-0033's wording allows it).
- #90: the coverage line labels a session `raw` (`MIN(u.src)`) when its main-agent usage is v1 and a subagent's is raw (valid under ADR-0039 §9).
- #90: hook rows show "?" for a missing event where the old code showed "unknown".
- #90: a session OTel joined partway through reads low, with no warning.
- #92: cache files deleted are `extracts/` and the current PROMPT_VERSION folder only; older-version part outputs stay.
- #92: the ops and health readers never show `held`.
- #92: an acknowledged condition-6 session stays held while the transcript still differs (each sweep files a new open row).
- #92: a resumed tail is derived alone; a tool call whose result lands in the tail is split across the cut (not probed).
- #93: a hung `launchctl print` reports "not installed"; the timed-out child is left running.
- #93: a plain file at `current` is overwritten without a message.
- #93: a healthy run takes ~0.2 s including Python startup, against the ~100 ms budget.
- #94: a dangling `local-process.md` symlink silently falls back to the master.
- #94: the source line shows a relative pointer unnormalised (`../..`).
- #94: house-master errors lack the `line N:` prefix the docstring promises.
- #94: a `## Process` heading inside a code fence is matched.
- #94: `docs/` (automation, flows, permissions, variables, architecture) still names `.claude/my-process.md`.
