# Flows

The runtime paths where data crosses a trust boundary or causes a side effect. Feature
behaviour (what the views show) is in [CONTEXT.md](../CONTEXT.md) and the ADRs; this is the
operations map. There is one actor throughout — the operator's macOS user — and no auth
anywhere, so "check" below means "what, if anything, stops this step", not a role lookup.
The standing guards: loopback binds (F1, F4), the read-only DB URI (F4), the live-session
guard (F3), self-exclusion of hindsight's own `claude -p` sessions (F3), and the pre-commit
denylist (`.githooks/pre-commit`, home paths / key shapes / transcript filenames) between
`local-data/` and the public repo.

## F1 — OTEL ingest (Claude Code → listener → DB)

**Actor:** Claude Code's OTLP exporter, configured by `~/.claude/settings.json`
(`OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318`, `OTEL_LOG_TOOL_DETAILS=1`).
**Precondition:** `com.hindsight.ingest` (launchd, `KeepAlive`) running. **Outcome:** rows in `otel_events` / `otel_metrics`.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. POST `/v1/logs` or `/v1/metrics` | `listener.py:146-176, 184` | Bind `127.0.0.1` only. No auth, no content-type check, no size cap. Any other path → `200 {}` with nothing stored | — |
| 2. Dechunk / gunzip / `json.loads` | `listener.py:131-154` | Any failure → whole batch dropped, `200` with `partialSuccess` | — |
| 3. Per-row insert | `listener.py:84-127` | Bad row counted and skipped; batch commits the rest. A malformed *container* yields zero rows and is not counted | INSERT `otel_events(event_name, session_id, timestamp, attributes)` / `otel_metrics(...)`, attributes stored as the full JSON dict |
| 4. Respond | `listener.py:168-176` | Always `200` | stderr → `~/Library/Logs/hindsight/listener.log` (exception text and skip counts; never bodies) |

**Deny case:** none exists; the protection is the bind address. **Failure that loses data:** DB locked past `busy_timeout=5000` → batch lost, reported as one rejected row, `200` (`listener.py:156, 165-167`).

## F2 — Self-instrumentation hook (Claude Code → hook.py → listener)

**Actor:** Claude Code firing `SessionStart`, `UserPromptSubmit`, `Stop` (wired in `~/.claude/settings.json`). **Outcome:** one `hindsight.hook` log record per firing.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. Read stdin | `hook.py:52-66, 85` | 0.5 s budget per blocking leg, 64 KiB chunks; unparseable → `{}` | — |
| 2. Build record | `hook.py:69-78, 96-107` | Only `session_id`, `hook_event_name`, two timings and — at `SessionStart` only — the inode of `cwd` (ADR-0018) leave the process. Prompt text, transcript path and tool input are discarded | `os.stat(cwd)`, read only |
| 3. POST `/v1/logs` | `hook.py:110-116` | 0.5 s connect+response timeout; response discarded unread | Row via F1 |
| 4. Exit | `hook.py:119-123` | Every exception swallowed; empty stdout/stderr | — |

**Cannot** block or modify the Claude Code action: no decision JSON, no non-zero exit. Listener down → event silently lost; the sync step's `fill_hook_identity` (F3) heals the race where the row lands after the session was synced.

## F3 — Analysis run (`python3 build/analyze.py`, manual or nightly)

**Actor:** operator (foreground) or `com.hindsight.nightly` at 03:00 with the installing shell's `PATH` baked in. **Precondition:** `claude` on PATH for the model steps; the mechanical steps run without it. **Outcome:** `sessions`, substrate tables, `audit`, `status_narrative`, `breakage`, `change_events`/`blobs`, `sunk_cost`, `project_presence` updated. Order is fixed at `analyze.py:1517-1581`.

| Step | Where | Check / gate | Side effect |
| --- | --- | --- | --- |
| 0. `init_db` — schema + one-shot migrations | `analyze.py:407-542` | `PRAGMA user_version` gates each sniff once per db. **v9 (ADR-0027):** resets the scanned marker of every session whose transcript survives and refills through step 4, so failed calls gain their text; a pruned transcript keeps its old rows with `error_text NULL` | `ALTER TABLE` adds (`error_text`, `agent_id`, identity columns); a v<9 db: DELETE all `SUBSTRATE_TABLES` rows for surviving sessions, full rescan, no model calls |
| 1. `sync_sessions` — glob `~/.claude/projects/*/*.jsonl` | `analyze.py:688-722` | Head-scan (first 50 lines, first 3,000 chars of the first user text) for one of four `ANALYSIS_SIGS` prompt signatures → `excluded_sessions`, never analysed (ADR-0003). Subagent transcripts are not sessions; they are scanned through their parent (ADR-0019) | INSERT `sessions` (status `pending`), `excluded_sessions` |
| 2. `redate_sessions`, `fill_hook_identity`, `observe_presence`, `canonicalize_projects` | `analyze.py:667-686, 725-746, 1444-1515` | Presence is skipped when the workspace root is unreadable (could not look ≠ all gone); a name counts as present only if it resolves to a live folder carrying the session's inode (ADR-0018) | Head-scans every surviving transcript; UPDATE `sessions.date`, `folder_identity`; UPSERT `project_presence`; UPDATE `sessions.project`, `status_narrative.project` to the folder's current name |
| 3. `invalidate_grown` | `analyze.py:819-885` | Skips live transcripts (mtime < 300 s on the parent or any subagent). Growth = parent larger than `sessions.size`, or a subagent transcript unseen/larger. Re-audit only if *parent* growth ≥ 25 % of `audited_size`; a shrunken transcript is left alone | DELETE substrate rows, unlink extract + cache files, status → `pending` |
| 4. `fill_substrate` | `substrate.py:332-395` | `skipped_records IS NULL` watermark; live guard. Parent + subagents in one pass, one commit per session | INSERT `tool_events`, `usage`, `command_grains`, `subagent_transcripts`, `field_histogram`; UPDATE `audit.adr_count`. **`tool_events.error_text`: the verbatim result content of a failed call — the one tool-result content the product stores (ADR-0027); `None` on success, uncapped** (`substrate.py:256-262, 271-280`) |
| 4a. `check_drift` | `analyze.py:904-997` | Newest record version with ≥ 20 records vs the nearest earlier one at or above the acknowledged baseline, against `substrate.FIELD_CONTRACT`; this run's skipped share vs the median of the last 7 runs (ADR-0020). Keys *added* under one version pair collapse to one row and dedup on the pair alone (#30). Wrapped in `try` — never halts the run | INSERT `breakage` (deduplicated against open rows), `scan_runs`; `osascript` notification for conditions 1 and 3 only, and only from the command line |
| 5. `classify_and_extract` — greedy extract of every selectable session | `analyze.py:1075-1096`, `extract.py` | Transcript and `.map.json` both missing → status `lost` (terminal) unless an audit row exists | Writes `local-data/analysis/extracts/<sid>.part*.txt` + `.map.json` — user/assistant text only, 1,500 chars per piece; tool results and file bodies excluded |
| 6. Per session: what-pass (`claude -p --model claude-haiku-4-5-20251001`, 300 s, `cwd=REPO`) | `analyze.py:1114-1201, 1250-1271` | **Boundary crossing: extract → model.** Output must strip to `SKIP` or start `###` (`valid_entry`) else session → `partial`, retried next run. `FileNotFoundError` or stderr containing "limit" → `LimitExhausted`, loop breaks | Raw output cached `local-data/analysis/what-v3/`; INSERT OR REPLACE `audit`; UPDATE `sessions.status`, `audited_size` |
| 7. `refresh_narratives` (skipped if paused) | `analyze.py:1204-1247`, `how.py:264-334` | Only for projects with a *valid* `.claude/my-process.md`, and only when the ledger hash, prompt version or model moved. Input is the run ledger — stage names (off-script runs included, #17), dates, audit titles — no transcript text. Write gated by `score.parse` + `contract` | INSERT OR REPLACE `status_narrative` |
| 8. `capture_backstop` | `analyze.py:1363-1394` | Hash compare against `backstop_state`; first sight is a silent baseline | **Full contents** of `~/.claude/{CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json}` and `installed_plugins.json` into `blobs`; `change_events(source='snapshot'\|'plugins-structural')` |
| 9. `_capture_project_git` | `analyze.py:1303-1329` | Per repo under `~/Documents/Claude` with `.git`; commits only, never the working tree | `git log/diff-tree/show -- .claude`; every historical `.claude/*` file version into `blobs`; `change_events(source='project-git')` |
| 10. `scan_sunk_cost` | `sunk_cost.py:176-267` | Reads today's filesystem: CLAUDE.md chains, skills, commands, `.mcp.json`, `~/.claude.json` | DELETE-all + INSERT `sunk_cost` (paths and token estimates, no bodies) |

**Failure modes:** a narrative or drift-guard exception is caught and printed; a model timeout returns `None` → `partial`; the run never deletes transcripts. stdout/stderr → `~/Library/Logs/hindsight/analyze.log` under launchd, including `claude --version` and the first 80 chars of rejected model output.

## F4 — Serve (`python3 build/serve.py` → browser)

**Actor:** operator's browser on `http://127.0.0.1:8321`. **Precondition:** DB exists with a `sessions` table (else exit 1, `serve.py:787-814`). **Outcome:** one HTML page per request.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. GET `/` (302 → `/what`), `/what`, `/where`, `/how` | `serve.py:760-784` | Loopback bind; no auth; other paths → 404; other methods → 501 | — |
| 2. Open DB `mode=ro` | `serve.py:86-90` | SQLite enforces read-only; WAL + 30 s timeout, so a writer's checkpoint waits rather than 500s | — |
| 3. Query | `serve.py:145-476`, `how.py:207-242, 355-392` | All values bound with `?`. The one request parameter, `?p=` on `/how`, is membership-checked against declaring projects before use; an unknown value falls back to the busiest and says so (`serve.py:659-663`) | — |
| 4. Read `.claude/my-process.md` of the chosen project | `how.py:179-189` | Strict YAML subset; any fault → whole declaration invalid, error text rendered escaped | Filesystem read outside the repo (workspace project dir) |
| 5. Render | `serve.py:696-757`, `what.js`, `where.js` | `html.escape` on every model- or DB-derived string server-side; `_blob()` guards `</script>`; JS `esc()` on every string, `inline()` re-adds `<b>`/`<code>` only | Reads `design/tokens.css` + `build/assets/*` per request (literal names only) |
| 5a. **Error text to the page** (ADR-0027, #33) | `serve.py:455-476, 482-496`, `where.js:106-123` | `where_data` ships **every** failed call's `error_text` verbatim in the where blob, whatever the filter — the first transcript content served. The error line is derived server-side (`error_line`: last non-empty line under a traceback, else first line after the fixed headers); the client only groups and escapes into `<pre>`. NULL text ships neither line nor text: counted, "not captured" | — |
| 5b. Session anchor `/what#<sid>` (ADR-0023) | `what.js:60-68` | Fragment never reaches the server. `CSS.escape` in the selector, `esc` in the miss note; never writes filter state — a row outside the filter is stated under the ledger | — |
| 6. Browser | `theme.js`, `chrome.js`, `how.js` | No fetch, no external URL; `localStorage.theme`, the per-tab `sessionStorage.filter` (issue #10), and `how.js` writing `?p=` back into that filter — the one link that writes state | — |

**No mutation route exists.** Refresh is a browser reload; a new run is F3. Screenshots of an opened league row may show real error lines: a per-image check for home paths and key shapes before `docs/screenshots/`, never an expanded traceback (its frames carry a path each) — the denylist cannot read a PNG.

## F5 — Operator commands (write, no model)

| Command | Where | Check | Side effect |
| --- | --- | --- | --- |
| `analyze.py acknowledge-breakage <id>` | `analyze.py:1031-1041, 1659-1678` | Open row only; exit 1 otherwise. Never a rescan (ADR-0020 §7) | UPDATE `breakage.acknowledged_at`; that version becomes the drift baseline |
| `analyze.py attribute <name> <folder> [--before]` | `analyze.py:748-816, 1627-1656` | Refuses (nothing written) on a missing db, unreadable folder or bad instant | UPDATE `sessions.folder_identity`, `attribution_source`; re-keyed by the next run |
| `listener.py install` / `analyze.py install` (+ `uninstall`) | `listener.py:210-230`, `analyze.py:1608-1624` | — | Write `~/Library/LaunchAgents/com.hindsight.{ingest,nightly}.plist`, `launchctl bootstrap`; log dir under `~/Library/Logs/hindsight` |

## Cross-flow invariants

- Write and read never share a process: F1/F3/F5 write, F4 reads `mode=ro` (ADR-0001, ADR-0008).
- Absence is never drawn as zero: pruned transcripts, dropped hook events, coverage gaps and uncaptured error text render as gaps or "not captured" (ADR-0001, 0013, 0015, 0027).
- The model never sees tool results, file contents, or anything from `~/.claude` other than message prose (F3 step 5); the narrative pass sees only the run ledger (F3 step 7).
- The only transcript content stored or served is the text of a failed tool call (F3 step 4, F4 step 5a); nothing of a successful one, and no tool input — any widening is its own ADR (ADR-0027 §2). It lives in `local-data/`, which is gitignored; the pre-commit denylist is the last line, not the first.
