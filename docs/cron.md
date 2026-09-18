# Scheduled and background work

Two launchd user agents and one Claude Code hook. `serve.py` is a foreground process with no job of its own; there is no other daemon (ADR-0001). Nothing here holds a secret: the nightly's model calls go through the operator's own `claude` login.

| Job | Schedule | Entry point | Secrets | Limits | Retry |
| --- | --- | --- | --- | --- | --- |
| Ingest listener `com.hindsight.ingest` | `RunAtLoad` + `KeepAlive` — always up, restarted by launchd on exit | `<sys.executable> build/listener.py` (no args → `127.0.0.1:4318`, default DB) | none | `busy_timeout` 5 s per request; `Content-Type` must start with `application/json` (`415`); bodies over `MAX_BODY` 8 MiB refused (`413`) or dropped (#34); no auth | none — a lost batch is one `partialSuccess` rejection and `200` |
| Nightly analysis `com.hindsight.nightly` | `StartCalendarInterval` 03:00 local; launchd runs it on wake if asleep, skips it if powered off | `<sys.executable> build/analyze.py`, `PATH` (and `HINDSIGHT_TZ`) baked from the installing shell | none | serial `claude -p` calls, 300 s each (`CALL_TIMEOUT`); drift notification via `osascript`, 30 s | pauses on `LimitExhausted` (rate limit, or no `claude` on `PATH`) — unreached sessions stay `pending`/`partial`; a failed extract or a gated-out output is retried next night |
| Self-instrumentation hook | per Claude Code hook event registered in `~/.claude/settings.json` (config, not code — snippet in `build/hook.py`'s docstring) | `python3 <clone>/build/hook.py [--port N]` | none | 0.5 s per blocking leg (stdin, connect, response) | none — fails silently; the firing is simply not recorded |

On-demand, never scheduled: `analyze.py acknowledge-breakage <id>` and `analyze.py attribute <name> <folder>`. Both open the DB through `init_db`, so either can be the first thing to fire a pending migration (below).

Install / remove: `python3 build/listener.py install|uninstall`, `python3 build/analyze.py install|uninstall`. Both write the plist under `~/Library/LaunchAgents/`, `launchctl bootout` (failure ignored) then `bootstrap gui/<uid>`. Plists bake install-time absolutes — re-run after moving the clone or changing Python. Inspect with `launchctl print gui/$(id -u)/com.hindsight.nightly`.

## Idempotency of the nightly run

A second run over unchanged input makes no model calls and no duplicate writes:

| Mechanism | Where | Effect |
| --- | --- | --- |
| `sessions.status` + `SELECTABLE` (`pending`, `partial`) | `analyze.py` `run_analysis` | `done`, `empty`, `lost` sessions never re-enter the model loop |
| `skipped_records IS NULL` as the scanned marker | `substrate.py` `fill_substrate` | Substrate (tool_events, usage, command_grains, field_histogram, subagent_transcripts) scanned once per session; a vanished transcript stays NULL, never a false empty |
| Growth top-up: `size` per session, `subagent_transcripts.size` per subagent | `analyze.py` `invalidate_grown` | A grown transcript, or a new/grown subagent transcript, has its substrate wiped and rescanned; shrunk or vanished is left alone (#13, ADR-0019) |
| `audited_size` watermark + `REAUDIT_SHARE = 0.25` | same | The audit is re-called only when ≥ 25 % of the transcript is unseen since the last audit, measured on the parent alone; imported sessions keep NULL and are never re-audited on size |
| Live-session guard, mtime < 300 s (`LIVE_WINDOW_S`) on the parent **or any subagent** | `substrate.py` `_is_live` | Skipped by the top-up, the scan and the model loop; stays pending for the next run |
| On-disk cache gated by `valid_entry` | `analyze.py` `call_cached` | Valid cached output reused, not re-called; a rejected output is logged and left uncached; a poisoned cache file is overwritten on the retry |
| `status_narrative` keyed on `(project, ledger_hash, prompt_version, model)` | `refresh_narratives` | Narrative re-called only when the ledger or prompt changes |
| `blobs` content-addressed, `INSERT OR IGNORE`; `backstop_state` last-seen hash/sha | `store_blob`, `capture_backstop` | Unchanged config and repos produce no rows; git capture is incremental |
| `breakage` open-row dedup | `check_drift` | One open row per (condition, old_version, new_version) — condition 1 also per key; keys added under one version pair are one row (#30). An open row is never re-raised; the spike check (condition 3) enters each run into `scan_runs` so a new normal stops tripping after ~4 runs |
| `PRAGMA user_version` | `init_db` | Each migration fires exactly once per DB |

Replaced wholesale each run: `sunk_cost`. Appended: substrate tables, `change_events`, `blobs`, `scan_runs`, `breakage`. Upserted: `audit`, `status_narrative`, `backstop_state`, `project_presence` (a history; rows update in place, never deleted — ADR-0018).

### The first run after a schema bump (v9, #32 / ADR-0027)

`init_db` runs the migration before anything else in the run — before sync, before the model loop. v9 calls `_reset_scanned`: every scanned session whose transcript still exists has its substrate rows deleted and its marker cleared in one transaction, then `fill_substrate` refills them all, committing per session. **No model calls**; audit rows, caches and `status` are untouched. ADR-0027 records it as seconds on this machine (the v8 rescan of the same shape took 4 s). Sessions whose transcript was pruned keep their old rows with `error_text` NULL — counted, not captured. A DB older than v8 is rescanned twice (v8 gate, then v9); correct, just slower. The rest of the night is a normal run. Whichever `analyze.py` command opens the DB first with the new code does this — the listener and `serve.py` never run migrations.

### The drift guard, every run

`check_drift` runs after the scan and never halts ingest — a guard exception is printed as `drift guard failed:` and the run continues (#15, ADR-0020). A trip writes a `breakage` row (banner on every view, red for conditions 1 and 3, blue for 2) and, for the red kind, pops a macOS notification — from the command line and the launchd job alike, both go through `main`. `acknowledge-breakage <id>` closes the row; its `new_version` becomes the comparison baseline. It never rescans: a parser fix is a code change plus a schema bump, which rescans through the mechanism above.

## Internal-call authentication

None present. The nightly job calls no HTTP endpoint. The hook → listener POST (`http://127.0.0.1:<port>/v1/logs`) carries no token. The listener checks two things (#34): `Content-Type` must start with `application/json` (`415` otherwise — a browser cannot send that cross-origin without a preflight, and there is no `OPTIONS` handler, so a web page the operator visits cannot post rows), and the body must stay under `MAX_BODY` 8 MiB declared, chunked or inflated. No auth beyond that; the protection is the loopback bind (see [flows.md](flows.md) F1/F2). Any local process sending JSON can write rows into `otel_events`.

## Where to see last runs

- Nightly: `~/Library/Logs/hindsight/analyze.log` — one `claude --version:` line per run, `rejected <file>: '<80 chars>'` for gated-out model output, `claude CLI not found on PATH — model calls paused this run`, `drift guard failed:`, `narrative pass failed:`. launchd appends; the file is never rotated.
- Listener: `~/Library/Logs/hindsight/listener.log` — startup line, `ingest error on <path>:`, `<path>: skipped N row(s)`, socketserver tracebacks. Never request bodies.
- In the product: every view's header carries the open breakage banner(s) with the acknowledge command; `/what` and `/how` state `synced through <date>` (`/what` adds the session count). `/how`'s coverage line is the cheapest "did last night run" check.
- `launchctl print gui/$(id -u)/<label>` for last exit status and whether the job is loaded.

## Concurrency between the two jobs and the server

The file is in WAL mode (issue #12): both writers' `init_db` set the pragma, and it persists in the file, so whichever opens it first switches it once. Readers never wait on a writer, and a page held open in `serve.py` never blocks a commit. The two writers serialise against each other: `analyze.py` waits up to 30 s for the listener, the listener up to 5 s (`busy_timeout`) for `analyze.py`. The nightly commits per session with the model call outside any transaction, so the residual is a single write held longer than 5 s landing on a listener insert: `capture_backstop` opens its transaction at the first blob and runs every repo's `git log`/`show` inside it; the schema-bump wipe in `_reset_scanned` is one transaction over the whole corpus. The readers (`serve.py`, `how.py`) open `mode=ro` with a 30 s timeout, for the brief checkpoint lock and for a DB no writer has switched yet.
