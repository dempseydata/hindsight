# Flows

The runtime paths where data crosses a trust boundary or causes a side effect. Feature
behaviour (what the views show) is in [CONTEXT.md](../CONTEXT.md) and the ADRs; this is the
operations map. There is one actor throughout — the operator's macOS user — so "authz check"
below means "what, if anything, stops this step", not a role lookup.

## F1 — OTEL ingest (Claude Code → listener → DB)

**Actor:** Claude Code's OTLP exporter, configured by `~/.claude/settings.json`
(`OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318`, `OTEL_LOG_TOOL_DETAILS=1`).
**Precondition:** `com.hindsight.ingest` running. **Outcome:** rows in `otel_events` / `otel_metrics`.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. POST `/v1/logs` or `/v1/metrics` | `listener.py:143-159` | Loopback bind only. No auth, no content-type check, no size cap. Any other path → `200 {}` with nothing stored. | — |
| 2. Dechunk / gunzip / `json.loads` | `listener.py:131-151` | Any failure → whole batch dropped, `200` with `partialSuccess` | — |
| 3. Per-row insert | `listener.py:86-98, 113-123` | Bad row counted and skipped; batch commits the rest. A malformed *container* yields zero rows and is not counted. | INSERT `otel_events(id, event_name, session_id, timestamp, attributes)` / `otel_metrics(...)`, attributes stored as the full JSON dict |
| 4. Respond | `listener.py:167-173` | Always `200` | stderr → `~/Library/Logs/hindsight/listener.log` (exception text and skip counts; never bodies) |

**Deny case:** none exists; the protection is the bind address. **Failure that loses data:** DB locked past `busy_timeout=5000` → batch lost, reported as one rejected row, `200` (`listener.py:153, 162-164`).

## F2 — Self-instrumentation hook (Claude Code → hook.py → listener)

**Actor:** Claude Code firing `SessionStart`, `UserPromptSubmit`, `Stop` (wired in `~/.claude/settings.json`, `timeout: 5`). **Outcome:** one `hindsight.hook` log record per event.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. Read stdin | `hook.py:46-69` | 0.5 s budget, 64 KiB chunks; unparseable → `{}` | — |
| 2. Build record | `hook.py:79-88` | Only `session_id` and `hook_event_name` leave the process; prompt text, transcript path and tool input are discarded | — |
| 3. POST `/v1/logs` | `hook.py:89-95` | 0.5 s connect+response timeout; response discarded | Row via F1 |
| 4. Exit | `hook.py:99-102` | Always exit 0, empty stdout/stderr | — |

**Cannot** block or modify the Claude Code action: no decision JSON, no non-zero exit. Listener down → event silently lost.

## F3 — Analysis run (`python3 build/analyze.py`, manual or nightly)

**Actor:** operator (foreground) or `com.hindsight.nightly` at 03:00. **Precondition:** `claude` on PATH. **Outcome:** `sessions`, `audit`, substrate tables, `status_narrative`, `change_events`/`blobs`, `sunk_cost`, `project_presence` updated. Order is fixed at `analyze.py:927-966`.

| Step | Where | Check / gate | Side effect |
| --- | --- | --- | --- |
| 1. `sync_sessions` — glob `~/.claude/projects/*/*.jsonl` | `analyze.py:461-475` | Head-scan first 3,000 chars for one of four hindsight prompt signatures → `excluded_sessions`, never analysed (ADR-0003) | INSERT `sessions` (status `pending`) |
| 2. `observe_presence`, `canonicalize_projects` | `analyze.py` | Skipped when the workspace root is unreadable (could not look ≠ all gone). A name counts as present only if it resolves to a live folder carrying the session's inode (ADR-0018); name-only sessions are checked by name alone and never re-keyed | UPSERT `project_presence` history rows (identity, name, first/last seen, present); UPDATE `sessions.project` and `status_narrative.project` to the folder's current name |
| 3. `invalidate_grown` | `analyze.py:487-533` | Skips live transcripts (mtime < 300 s). Re-audit only if growth ≥ 25 % of `audited_size` | DELETE substrate rows, unlink extract + cache files, status → `pending` |
| 4. `fill_substrate` | `substrate.py:216-232` | `skipped_records IS NULL` watermark; live guard | INSERT `tool_events`, `usage`, `command_grains`; UPDATE `audit.adr_count` |
| 5. `classify_and_extract` — greedy extract of every selectable session | `analyze.py:568-584`, `extract.py` | Transcript and `.map.json` both missing → status `lost` (terminal) unless an audit row exists | Writes `local-data/analysis/extracts/<sid>.part*.txt` + `.map.json` — user/assistant text only, 1,500 chars per piece, tool results and file bodies excluded |
| 6. Per session: what-pass (`claude -p`) | `analyze.py:598-693, 745-761` | **Boundary crossing: extract → model.** Output must strip to `SKIP` or start `###` (`valid_entry`) else session → `partial`, retried next run. `FileNotFoundError` or stderr containing "limit" → `LimitExhausted`, loop breaks | Raw output cached `local-data/analysis/what-v3/`; INSERT OR REPLACE `audit`; UPDATE `sessions.status`, `audited_size` |
| 7. `refresh_narratives` (skipped if paused) | `analyze.py:697-739`, `how.py:295` | Only for projects with a *valid* `.claude/my-process.md`. Input is audit titles + stage names, no transcript text. Write gated by `score.parse` + `contract` (traced, dated, `Now` present, within `BOUNDS`) | INSERT OR REPLACE `status_narrative` |
| 8. `capture_backstop` | `analyze.py:864-876` | Hash compare against `backstop_state` | **Full contents** of `~/.claude/{CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json}` and `installed_plugins.json` into `blobs`; `change_events(source='snapshot'|'plugins-structural')` |
| 9. `_capture_project_git` | `analyze.py:790-883` | Per repo under `~/Documents/Claude` with `.git`; first sight is a silent baseline | `git log/diff-tree/show -- .claude`; every historical `.claude/*` file version into `blobs`; `change_events(source='project-git')` |
| 10. `scan_sunk_cost` | `sunk_cost.py:231-266` | — | DELETE-all + INSERT `sunk_cost` (paths and token estimates, no bodies) |

**Failure modes:** any narrative exception is caught and printed (`analyze.py:954-960`); a model timeout returns `None` → `partial`; the run never deletes transcripts. stdout/stderr → `~/Library/Logs/hindsight/analyze.log` under launchd, including the first 80 chars of rejected model output.

## F4 — Serve (`python3 build/serve.py` → browser)

**Actor:** operator's browser on `http://127.0.0.1:8321`. **Precondition:** DB exists with a `sessions` table (else exit 1, `serve.py:621-648`). **Outcome:** one HTML page per request.

| Step | Where | Check | Side effect |
| --- | --- | --- | --- |
| 1. GET `/`, `/what`, `/where`, `/how` | `serve.py:596-605` | Loopback bind; no auth; other paths → 404; other methods → 501 | — |
| 2. Open DB `mode=ro` | `serve.py:85` | SQLite enforces read-only. No `busy_timeout`: a writer's exclusive lock → unhandled `OperationalError` → 500 | — |
| 3. Query | `serve.py`, `how.py:224, 316, 344` | All values bound with `?`. The one request parameter, `?p=` on `/how`, is membership-checked against DB project names before use (`serve.py:496`) | — |
| 4. Read `.claude/my-process.md` of the chosen project | `how.py:174, 331` | Strict YAML subset; any fault → whole declaration invalid, error text rendered escaped | Filesystem read outside the repo (workspace project dir) |
| 5. Render | `serve.py:370-590`, `what.js`, `where.js` | `html.escape` on every model- or DB-derived string server-side; `_blob()` guards `</script>`; JS `esc()` on names, `inline()` re-adds `<b>`/`<code>` only | Reads `design/tokens.css` + `build/assets/*` per request (literal names only) |
| 6. Browser | `theme.js` | No fetch, no external URL; `localStorage.theme` only | — |

**No mutation route exists.** Refresh is a browser reload; a new run is F3.

## Cross-flow invariants

- Write and read never share a process: F1/F3 write, F4 reads `mode=ro` (ADR-0001, ADR-0008).
- Absence is never drawn as zero: pruned transcripts, dropped hook events and coverage gaps render as gaps (ADR-0001, 0013, 0015).
- The model never sees tool results, file contents, or anything from `~/.claude` other than message prose (F3 step 4); the narrative pass sees only audit titles (F3 step 6).
