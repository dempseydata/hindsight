# Flows

The runtime paths where data crosses a trust boundary or causes a side effect. Feature
behaviour (what the views show) is in [CONTEXT.md](../CONTEXT.md) and the ADRs; this is the
operations map. There is one actor throughout — the operator's macOS user — and no auth
anywhere, so "check" below means "what, if anything, stops this step", not a role lookup.
`<home>` is Hindsight home: `$HINDSIGHT_HOME`, else `~/.hindsight` (`home.py:19-20`); the
store is `<home>/hindsight.db`. The standing guards: loopback binds (F1, F4), the listener's
Content-Type gate (F1), the read-only DB URI (F4, F6), the append-integrity hash (F2),
flock single-flight of the analysis run (F3), the live guards (F3), self-exclusion of
hindsight's own `claude -p` sessions (F3), fail-closed compaction (F3 step 11), and the
pre-commit hook (`.githooks/pre-commit`: `claude plugin validate`, then the denylist of home
paths / key shapes / transcript filenames plus a private-name list kept outside the repo)
between `local-data/` and the public repo. Permissions per process: [permissions.md](permissions.md).

![One session after it ends: transcript lines go through the capture hook into the raw store; the nightly run extracts and derives, sends the extract to claude -p, and records facts in hindsight.db; the views read them on loopback, with OTel from the listener as a side input](diagrams/dataflow.svg)

F2 → F3 → F4 for one session, as an [Archify](https://github.com/tt-a1i/archify) export of [diagrams/dataflow.archify.json](diagrams/dataflow.archify.json), checked against the code. Extraction and derivation are one node, and the what-pass and status pass share the `claude -p` node; the output gates and the sweep are on its side cards.

## F1 — OTEL ingest (Claude Code → listener → DB)

**Actor:** Claude Code's OTLP exporter, configured by `~/.claude/settings.json`
(`OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318`, `OTEL_LOG_TOOL_DETAILS=1`) — or any
local process that can reach loopback. **Precondition:** `com.hindsight.ingest` (launchd,
`RunAtLoad` + `KeepAlive`) running; `make_server` creates the db file and the `otel_*` tables
if absent (`listener.py:53-61, 239-243`). **Outcome:** rows in `otel_events` / `otel_metrics`,
the `listener` health row updated.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. POST `/v1/logs` or `/v1/metrics` | `listener.py:166-176, 241` | Bind `127.0.0.1` only. No auth. `Host` not naming loopback → `403` (DNS-rebinding guard). `Content-Type` not starting `application/json` → `415`; declared `Content-Length` over `MAX_BODY` 8 MiB → `413`, body unread (#34). No OPTIONS handler, so a cross-origin JSON POST cannot preflight | — |
| 2. Dechunk / gunzip / `json.loads` | `listener.py:143-158, 178-187` | Chunked running total or inflated body over `MAX_BODY`, a truncated gzip stream, or any parse failure → whole batch dropped, `200` with `partialSuccess`. **A negative chunk size passes the cap check and `rfile.read(<0)` reads to EOF, uncapped** | — |
| 3. Per-row insert | `listener.py:88-139, 188-197` | Bad row counted and skipped; batch commits the rest. A malformed *container* yields zero rows and is not counted. **Any other POST path:** body parsed, nothing stored, `200 {}`, and a health *success* written | INSERT `otel_events(event_name, session_id, timestamp, attributes)` / `otel_metrics(...)`, attributes stored as the full JSON dict (resource `service.name`/`service.version` merged in) |
| 4. Respond | `listener.py:202-211, 213-233` | `200` for any accepted body. `GET /health` → `200 {"ok": true}`, any other GET → `404` (#37, a liveness probe; no DB touch) | UPSERT `health` (`listener`; error text on a dropped batch). stderr → `<home>/logs/listener.log` under launchd (`--log`; exception text and skip counts; never bodies) |

**Deny case:** `403` on a `Host` that does not name loopback (the DNS-rebinding guard), `415` on a non-JSON content type, `413` on an over-cap declared length (`Handler._refuse`, one stderr line each); otherwise the protection is the bind address. **Not denied:** any local process can post forged events; those feed the where view's token source (`serve.tok_sql`), the cross-check (F3 step 4a) and the health check's capture-behind line (F6). **Store failure:** DB locked past `busy_timeout=5000`, or any `sqlite3.OperationalError` → the transaction rolls back, a health error is written, and the batch is answered `503` with `Retry-After: 5`; the OTel exporter resends it (it retries 429/502/503/504). Per-row handlers re-raise these, so a lock is never counted as a skipped row. If the operator enables OTel prompt logging, prompt text lands verbatim in `otel_events.attributes`; nothing filters it.

## F2 — Capture hook (Claude Code → capture.py → raw store)

**Actor:** Claude Code firing `SessionStart`, `Stop` or `SubagentStop`, registered by the plugin's `hooks/hooks.json` with `"async": true`, so the turn never waits (ADR-0033, ADR-0036). **Precondition:** none — `analyze.init_db` creates `<home>` and the db, and runs any pending migration (F3 step 0) outside the analysis flock. **Outcome:** verbatim transcript lines past the high-water in `raw_records`; the `capture` health row updated.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. Read stdin | `capture.py:49-62, 194` | 0.5 s budget, 64 KiB chunks; unparseable → silent exit | — |
| 2. Gate | `capture.py:41-42, 197-199` | A JSON object whose `hook_event_name` is one of the three and whose `transcript_path` ends `.jsonl`; anything else is a no-op. **No containment check:** any readable `.jsonl` path in a payload is captured | — |
| 3. Identity of the transcript | `capture.py:65-72` | Session and agent come from the **path** (`<sid>.jsonl`, `<sid>/subagents/agent-<id>.jsonl`), never the payload's ids (ADR-0039 §4) | — |
| 4. SessionStart: folder identity | `capture.py:138-155` | `os.stat(cwd).st_ino`; missing cwd records nothing; first write wins on resume (ADR-0018) | UPSERT `transcripts.folder_identity` |
| 5. Stop / SubagentStop: capture | `capture.py:91-126, 177-189` | `BEGIN IMMEDIATE` (30 s busy wait) so two firings serialise; the last stored line is re-hashed (SHA-256) against `last_hash`. A trailing partial line waits. SubagentStop captures the agent file and the parent; a missing one is skipped | INSERT OR IGNORE `raw_records` (each line zlib-compressed, newline included); advance `transcripts.high_water`, `last_hash`, `last_size` — one transaction |
| 6. Hash mismatch (transcript rewritten) | `capture.py:129-135` | One open `breakage` row per session (condition 6) | Nothing appended until acknowledged; compaction holds the session (F3 step 11) |
| 7. Finish | `capture.py:202-218` | Any exception rolled back and recorded; nothing raised into the session; no stdout | UPSERT `health` (`capture`) |

**Cannot** block or modify the Claude Code action: async, no decision JSON, no output. A missed firing is caught up by the run's sweep (F3 step 1), which calls the same `capture`.

## F3 — Analysis run (`python3 cli/analyze.py`, manual or nightly)

**Actor:** operator (foreground) or `com.hindsight.nightly` at 03:00 with the installing shell's `PATH`, and, when set, `HINDSIGHT_HOME`, `HINDSIGHT_TZ`, `HINDSIGHT_RAW_DAYS` and `CLAUDE_PLUGIN_DATA` baked in at install (`hindsight.py:56-59`, ADR-0034 §2); an install written before the raw limit was baked lacks `HINDSIGHT_RAW_DAYS` and compacts at 90 days until `/hindsight:ops install` is re-run. **Precondition:** `claude` on PATH for the model steps; the mechanical jobs run without it. **Outcome:** raw store caught up; `sessions`, derived tables, `breakage`, `audit`, `status_narrative`, `change_events`/`blobs`, `sunk_cost`, `project_presence` updated; old raw records compacted; the `analysis` health row written. One ordered job list, each job failing alone (ADR-0038), at `analyze.py:2063-2103`.

| Step | Where | Check / gate | Side effect |
| --- | --- | --- | --- |
| Lock | `analyze.py:1988-2011` | `flock(LOCK_EX\|LOCK_NB)` on `<db dir>/analysis.lock`; held → print and exit. Released with the process. Only the run takes it: capture (F2), the listener (F1) and the F5 write commands do not, and rely on SQLite's write lock | Creates `analysis.lock` |
| 0. `init_db` — schema + one-shot migrations | `analyze.py:410-554, 651-707` | `PRAGMA user_version` gates each sniff once per db; a failure here runs no job. v7 rebuilds `project_presence` inside an explicit `BEGIN`; v10 adds the raw store in one transaction, then a full `VACUUM` | Destructive one-shots on old dbs: v<1 drops the why-pass tables and dedupes `tool_events`; v2 deletes refusal `audit` rows; v10 rebuilds `breakage`; v11 drops `audit.date`; v12 drops `scan_runs`; v13 rewrites unredacted blobs and `VACUUM`s |
| 1. `sweep` | `analyze.py:759-782` | `capture` (F2) over every `<root>/*/*.jsonl` and `*/*/subagents/agent-*.jsonl` larger than its high-water; a vanished file is skipped | `raw_records`, `transcripts`, condition-6 `breakage` |
| 2. Bookkeeping: `sync_sessions`, `fill_hook_identity`, `observe_presence`, `canonicalize_projects` | `analyze.py:785-832, 1829-1899` | Sessions come from the registry (parents with captured bytes). Head-scan of the first 52 stored lines, first 3,000 chars of the first user text, for one of four `ANALYSIS_SIGS` → `excluded_sessions`, never analysed (ADR-0003). Presence is skipped when the workspace root is unreadable; a name counts only if it resolves to a live folder carrying the session's inode (ADR-0018) | INSERT `sessions` (status `pending`), `excluded_sessions`; UPDATE `sessions.folder_identity`; UPSERT `project_presence`; UPDATE `sessions.project`, `status_narrative.project` to the folder's current name |
| 3. `invalidate_grown` | `analyze.py:907-953` | Growth = registry high-water above `sessions.size`. Skips a live transcript (mtime < 300 s on the parent or any subagent, if the file exists). Re-audit only if `done`, not compacted, and ≥ 25 % of the high-water is past `audited_size`; a shrunken one is left alone | UPDATE `size`; unlink extract + what-cache files; status → `pending` on re-audit |
| 4. Derivation | `analyze.py:990-1030, 1083-1114`, `substrate.py` | A session is due when its newest raw rowid exceeds its `deriver_state`; its `raw` rows are wiped and re-derived from all its raw records, one transaction per session; a failure rolls back that session alone. **No live guard.** A non-JSON-object line → condition-5 `breakage` | `records_index`, `usage`, `tool_events`, `command_grains`, `field_histogram`, `otel_histogram`, `deriver_state`. **`tool_events.error_text`: the verbatim result content of a failed call — the one tool-result content the product stores (ADR-0027); `None` on success, uncapped** (`substrate.py:271, 280`) |
| 4a. Drift guard, cross-check | `analyze.py:1178-1331` | Skipped if derivation failed or any session is still due. Drift: newest record version with ≥ 20 records vs the nearest earlier one at or above the acknowledged baseline, against the derivers' declared `FIELD_CONTRACT`; the OTel histogram likewise against `OTEL_DECLARED` (ADR-0037). Condition 3 is retired. Cross-check: per completed day, OTel vs transcript input-side tokens, gap > 5 % (condition 4) | INSERT `breakage`, deduplicated against open rows; `osascript` notification for conditions 1 and 4, from every CLI invocation — the nightly included (`notify=True`, `analyze.py:2195`) |
| 5. `classify_and_extract` | `analyze.py:1404-1467`, `extract.py` | Skips sessions whose newest raw record was captured < 300 s ago (`held_live`). No parent raw records and no cached `.map.json` → `lost` (terminal), or `done` if an audit row stands | Feeds the parent's raw records to `extract.py` on stdin; writes `<work dir>/extracts/<sid>.part*.txt` + `.map.json` (work dir `$CLAUDE_PLUGIN_DATA/analysis`, else `local-data/analysis`) — user/assistant text only, 1,500 chars per message; tool results dropped, Edit/Write targets kept as markers |
| 6. Per session: what-pass (`claude -p --model claude-haiku-4-5-20251001 --tools "" --strict-mcp-config --settings {"disableAllHooks": true}`, 300 s, cwd a fixed empty folder under the temp dir) | `analyze.py:1485-1572, 1625-1656` | **Boundary crossing: extract → model.** Serial, no per-run call cap. Output must strip to `SKIP` or start `###` (`valid_entry`), else uncached and session → `partial`, retried next run. `FileNotFoundError`, or a non-zero exit whose output matches the CLI's usage-stop lines (`LIMIT_RE`) → `LimitExhausted`, loop pauses with one stderr line | Valid output cached `<work dir>/what-v3/`; INSERT OR REPLACE `audit`; UPDATE `sessions.status`, `audited_size`. The child writes its own transcript under `~/.claude/projects/`, which the next sweep captures verbatim and step 2 excludes |
| 7. `refresh_narratives` (skipped if paused) | `analyze.py:1575-1618`, `how.py:209-238, 440-450` | Only for projects whose declaration resolves valid (root `local-process.md`, else the house master named in `~/.claude/CLAUDE.md`, ADR-0032), and only when the ledger hash, prompt version or model moved. Input is the run ledger (stage names, dates, audit titles) plus the project's ADR headers (ADR-0035) — no transcript text. Write gated by `score.parse` + `contract_v2` | INSERT OR REPLACE `status_narrative`; `git log` per ADR file |
| 8. `capture_backstop` | `analyze.py:1659-1779` | Hash compare against `backstop_state`; first sight is a silent baseline | Contents of `~/.claude/{CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json}` and `plugins/installed_plugins.json`, redacted (`redact.py`), into `blobs`; `change_events(source='snapshot'\|'plugins-structural')` |
| 9. `_capture_project_git` | `analyze.py:1688-1714` | Per repo under the workspace root with `.git`; commits only, never the working tree | `git log/diff-tree/show -- .claude`; every historical `.claude/*` file version, redacted, into `blobs`; `change_events(source='project-git')` |
| 10. `scan_sunk_cost` | `sunk_cost.py:176-267` | Reads today's filesystem: CLAUDE.md chains with `@`-imports, skills, commands, `.mcp.json`, `~/.claude.json` | DELETE-all + INSERT `sunk_cost` (paths and token estimates, no bodies) |
| 11. `compact` | `analyze.py:1902-1985` | `HINDSIGHT_RAW_DAYS` (default 90, `0` = never); a negative or non-numeric value raises and deletes nothing. Held (counted, kept): status `pending`/`partial`, an open condition-6 breakage, or any deriver still due. A session with no timestamped record is kept (ADR-0034) | Per session, one transaction: DELETE `raw_records` and its `deriver_state`, `raw` derived rows → `compacted`; unlink cached extract + outputs; `incremental_vacuum`. Registry and audit rows stay. **Irreversible** |
| 12. Health | `analyze.py:2102-2103` | — | UPSERT `health` (`analysis`): failed jobs, active raw limit, held count |

**Failure modes:** a job's exception is rolled back, printed and recorded, and the next job runs; a model timeout returns `None` → `partial`. The run never deletes transcripts; it deletes raw records only through step 11. stdout/stderr → `<home>/logs/analyze.log` under launchd (`--log`), including `claude --version`, compaction counts and the first 80 chars of rejected model output.

## F4 — Serve (`python3 cli/serve.py` → browser)

**Actor:** operator's browser on `http://127.0.0.1:8321`. **Precondition:** DB exists with a `sessions` table (else exit 1, `serve.py:889-916`). **Outcome:** one HTML page per request.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. GET `/` (302 → `/what`), `/what`, `/where`, `/how` | `serve.py:862-886` | Loopback bind; no auth; `Host` not naming loopback → `403`; other paths → 404 (`VIEWS` allowlist); other methods → 501 (stdlib) | One request line on stderr (stdlib `log_message`: time, path, query, status) → `<home>/logs/serve.log` when started by `/hindsight:ops`; the view-use record (ticket 119). Never the DB (ADR-0008) |
| 2. Open DB `mode=ro` | `serve.py:94-98` | SQLite enforces read-only; WAL + 30 s timeout, so a writer's checkpoint waits rather than 500s. The path is URL-quoted, as in `health.py:116` and the `how.py` smoke entry | — |
| 3. Query | `serve.py:101-537`, `how.py:256-292` | All values bound with `?`. The one request parameter, `?p=` on `/how`, is membership-checked against `declaring_projects` before use; an unknown value is escaped into a note and falls back to the busiest (`serve.py:717-729`) | — |
| 4. Resolve the chosen project's process | `serve.py:567-573`, `how.py:192-238, 440-450` | Root `local-process.md`, else the house master named under `## Process` in `~/.claude/CLAUDE.md` (ADR-0032); strict YAML subset, any fault → declaration invalid, error text rendered escaped | Filesystem reads outside the repo (every DB project's `local-process.md`, the master, `docs/adr/*.md`); `git log` per ADR file for a valid declaration |
| 5. Render | `serve.py:743-860`, `what.js`, `where.js` | `html.escape` on every model- or DB-derived string server-side; `_blob()` writes every `<` in the inline JSON as its escape, so neither `</script>` nor `<!--` can reach the script's raw text (#58); JS `esc()` on every string (`& < > "`), `inline()` re-adds `<b>`/`<code>` only. One gap: `data-id="${r.id}"` is unescaped (`what.js:33`); ids are transcript filename stems, which a capture payload can choose (F2 step 2) | Reads `design/tokens.css` + `cli/assets/*` per request (literal names only) |
| 5a. **Error text to the page** (ADR-0027, #33) | `serve.py:512-553`, `where.js:166-175` | `where_data` ships **every** failed call's `error_text` verbatim in the where blob, whatever the filter — the first transcript content served. The error line is derived server-side (`error_line`: last non-empty line under a traceback, else first line after the fixed headers); the client only groups and escapes into `<pre>`. NULL text ships neither line nor text: counted, "not captured" | — |
| 5b. Session anchor `/what#<sid>` (ADR-0023) | `what.js:146-151` | Fragment never reaches the server. `CSS.escape` in the selector, `esc` in the miss note; never writes filter state — a row outside the filter is stated under the ledger | — |
| 6. Browser | `theme.js`, `chrome.js`, `how.js` | No fetch, no external URL; `localStorage.theme`, the per-tab `sessionStorage.filter` (issue #10), and `how.js` writing `?p=` back into that filter — the one link that writes state | — |

**No mutation route exists.** Refresh is a browser reload; a new run is F3. **Deny case:** `403` on a `Host` that does not name loopback, so a DNS-rebinding page — same-origin once its hostname resolves to `127.0.0.1` — cannot read the views. Any local process still can. Screenshots of an opened league row may show real error lines: a per-image check for home paths and key shapes before `docs/screenshots/`, never an expanded traceback (its frames carry a path each) — the denylist cannot read a PNG.

## F5 — Operator commands (write, no model)

None of these takes the analysis flock (F3 Lock); each that opens the store runs `init_db`, so pending migrations can run from here too.

| Command | Where | Check | Side effect |
| --- | --- | --- | --- |
| `analyze.py acknowledge-breakage <id>` | `analyze.py:1376-1386, 2141-2160` | DB must exist; integer id; open row only; exit 1 otherwise. Never a rescan (ADR-0020 §7) | UPDATE `breakage.acknowledged_at`; a drift row's version becomes the baseline; a condition-6 row lets capture and compaction proceed |
| `analyze.py attribute <name> <folder> [--before]` | `analyze.py:835-901, 2109-2138` | Refuses (nothing written) on a missing db, a folder not there or outside the workspace root, or a bad instant | UPDATE `sessions.folder_identity`, `attribution_source`; UPSERT `project_presence`; re-keyed by the next run |
| `import_backfill.py` | `import_backfill.py:58-97` | Skips any id already in `sessions`; no model calls | INSERT `sessions`, `audit` from `local-data/backfill/` |
| `/hindsight:ops install [--from <path>]` | `hindsight.py:51-69, 84-130` | User-invoked only (`disable-model-invocation`). Exact argument shapes, else usage and exit 2 (`hindsight.py:208-220`). `--from` refuses if `<home>/hindsight.db` exists or the source is not a file | Create `<home>/logs`; move v1 logs in, never over an existing file; re-point `<home>/current` → plugin root; write `~/Library/LaunchAgents/com.hindsight.{ingest,nightly}.plist`, `launchctl bootout` + `bootstrap`; `--from` boots out both jobs first and moves the db with its `-wal`/`-shm` into home. Reads `~/.claude/settings.json` to print v1 hook entries; never writes it |
| `/hindsight:ops uninstall` | `hindsight.py:133-142` | — | `launchctl bootout` both; delete both plists; unlink `current` only if it is a symlink. Never the database or logs; prints `rm -rf <home>` |
| `/hindsight:ops start` / `stop` | `hindsight.py:145-158` | `start` refuses if the ingest plist is absent | `launchctl bootout` + `bootstrap` / `bootout` of `com.hindsight.ingest` |
| `/hindsight:ops serve` / `open` | `hindsight.py:161-205` | Starts serve only if `:8321` does not answer; **any** HTTP answer counts as "ours", so a squatter on the port gets the browser. `open` reports failure if the server exits within 10 s | `serve.py` detached (`start_new_session`), log `<home>/logs/serve.log`; `open http://127.0.0.1:8321/what` |

## F6 — Health check (Claude Code → health.py, synchronous)

**Actor:** Claude Code firing `SessionStart` (`hooks/hooks.json`, 5 s timeout; ADR-0036 §6). **Precondition:** none. **Outcome:** silence when healthy, else one `systemMessage` line shown to the operator, not the model.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. Installed? | `health.py:110-114` | DB file present and `launchctl print gui/<uid>/<label>` zero for both jobs, else "not installed" | — |
| 2. Repoint | `health.py:58-69, 115` | Refuses (warns) if `current` is a real directory. Unchanged when it already resolves to `$CLAUDE_PLUGIN_ROOT` | Atomic re-link of `<home>/current` to `$CLAUDE_PLUGIN_ROOT`; `launchctl kickstart -k` restarts the listener |
| 3. Read the store | `health.py:72-107, 116-122` | `file:<quoted path>?mode=ro`, 1 s timeout; an un-migrated store → silence. Reports failing sources and "capture behind OTel" (an OTel `Stop` for another session more than 120 s past its last capture) | — |
| 4. Report | `health.py:136-143` | Any exception becomes a message line; never blocks the session | stdout JSON only when there is something to say |

`$CLAUDE_PLUGIN_ROOT` decides which code the KeepAlive listener and the nightly run next (through `current`).

## Cross-flow invariants

- Write and read never share a process: F1/F2/F3/F5 write, F4 and F6 read `mode=ro` (ADR-0001, ADR-0008). F6's one write is the `current` symlink.
- Absence is never drawn as zero: pruned transcripts, compacted records, dropped OTel events, coverage gaps and uncaptured error text render as gaps or "not captured" (ADR-0001, 0013, 0015, 0027, 0034).
- The model never sees tool results, file contents, or anything from `~/.claude` other than message prose (F3 steps 5-6); the narrative pass sees only the run ledger and ADR headers (F3 step 7). There is no redaction of what the operator typed (ADR-0034).
- The raw store holds every captured transcript line verbatim until compaction (F2, F3 step 11), including hindsight's own `claude -p` transcripts. The only transcript content *served* is the text of a failed tool call (F3 step 4, F4 step 5a); any widening is its own ADR (ADR-0027 §2). It lives in the DB in Hindsight home, outside the repo; the pre-commit denylist is the last line, not the first.
