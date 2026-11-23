# Scheduled and background work

Two launchd user agents and two Claude Code hooks. `serve.py` is an on-demand process with no job of its own (`/hindsight:ops serve|open` starts it detached, no plist); there is no other daemon (ADR-0001). Nothing here holds a secret: the nightly's model calls go through the operator's own `claude` auth.

| Job | Schedule | Entry point | Secrets | Limits | Retry |
| --- | --- | --- | --- | --- | --- |
| Ingest listener `com.hindsight.ingest` | `RunAtLoad` + `KeepAlive` — always up, restarted by launchd on exit | `<sys.executable> <home>/current/cli/listener.py --log` (→ `127.0.0.1:4318`, default DB `<home>/hindsight.db`; `HINDSIGHT_HOME` baked in if set) | none | `busy_timeout` 5 s per request; `Content-Type` must start with `application/json` (`415`); declared body over `MAX_BODY` 8 MiB `413`, chunked or inflated over it dropped (#34); no auth | none — a failed body is counted, answered `200` with `partialSuccess`, and not retried |
| Nightly analysis `com.hindsight.nightly` | `StartCalendarInterval` 03:00 local; launchd runs it on wake if asleep, skips it if powered off | `<sys.executable> <home>/current/cli/analyze.py --log`, `PATH` (and, when set, `HINDSIGHT_HOME`, `HINDSIGHT_TZ`, `HINDSIGHT_RAW_DAYS`, `CLAUDE_PLUGIN_DATA`) baked from the installing shell; re-run `ops install` after changing any of them | none | serial `claude -p` calls, 300 s each (`CALL_TIMEOUT`); **no cap on calls, sessions or tokens per run**; drift notification via `osascript`, 30 s | each job fails alone (ADR-0038); pauses on `LimitExhausted` (a usage-stop line matching `LIMIT_RE`, or no `claude` on `PATH`) — unreached sessions stay `pending`/`partial`; a failed extract or a gated-out output is retried next night, unbounded |
| Capture hook | `SessionStart`, `Stop`, `SubagentStop`, `async: true` (`hooks/hooks.json`, ADR-0033) | `python3 "${CLAUDE_PLUGIN_ROOT}/cli/capture.py"` | none | 0.5 s stdin budget; no `timeout` set, so Claude Code's default applies; opens the DB through `init_db` (30 s) | none per firing — the nightly sweep captures anything past the high-water |
| Health hook | `SessionStart`, synchronous, `timeout: 5` (ADR-0036 §6) | `python3 "${CLAUDE_PLUGIN_ROOT}/cli/health.py"` | none | 0.05 s stdin; 1 s per `launchctl` call (two `print`, maybe one `kickstart`); 1 s read-only SQLite. ADR-0036 budgets ~100 ms; not enforced | none — runs again at the next session |

On-demand, never scheduled: `analyze.py` itself, `analyze.py acknowledge-breakage <id>`, `analyze.py attribute <name> <folder>`, `import_backfill.py`. All open the DB through `init_db`, so any can be the first thing to fire a pending migration (below) — as can the capture hook.

Install / remove: `/hindsight:ops install|uninstall` (`cli/hindsight.py`). `install` creates `<home>/logs` (moving v1's logs from `~/Library/Logs/hindsight` once), points `<home>/current` at the plugin root, writes both plists under `~/Library/LaunchAgents/`, then `launchctl bootout` (failure ignored) and `bootstrap gui/<uid>` for each — idempotent, and it replaces v1's plists in place. It prints any `~/.claude/settings.json` hook entries still pointing at v1's hook for the operator to remove, and never edits that file; it warns when `CLAUDE_PLUGIN_DATA` is unset. `install --from <path>` first moves a v1 database (and its `-wal`/`-shm`) into Hindsight home, refusing if one is already there. `uninstall` boots out both jobs and deletes both plists and `current`, never the database; it prints `rm -rf <home>` as the manual step. `start|stop` bootstrap or boot out the ingest job only. No flag reaches the jobs: `install` passes neither `--port` nor `--projects-dir`. The health hook re-points `current` on a plugin update; re-run `install` after changing Python or a baked variable. Inspect with `launchctl print gui/$(id -u)/com.hindsight.nightly`.

## Idempotency of the nightly run

A second run over unchanged input makes no model calls and no duplicate writes:

| Mechanism | Where | Effect |
| --- | --- | --- |
| Single-flight `flock` on `<db dir>/analysis.lock` | `run_analysis` (ADR-0038 §5) | A second run exits 0 with one log line, no health write |
| Raw store keyed `(session, agent, byte_offset)`, `INSERT OR IGNORE`; high-water + last-line hash | `capture` (hook and sweep) | Re-capture writes nothing; a changed prefix is one condition-6 `breakage` row per session, nothing appended |
| `sessions.status` + `SELECTABLE` (`pending`, `partial`) | `what_pass` | `done`, `empty`, `lost` sessions never re-enter the model loop |
| `deriver_state` keyed `name@version`, newest raw rowid per session | `derive` (ADR-0031 §6) | A session is re-derived only when it has new raw records or the deriver's version bumped; a failure rolls back that session alone and leaves it due |
| `audited_size` watermark + `REAUDIT_SHARE = 0.25` | `invalidate_grown` | The audit is re-called only when ≥ 25 % of the parent transcript is unseen since the last audit; imported and compacted sessions are never re-audited on size |
| What-pass live guard: newest raw record captured < 300 s ago (`LIVE_WINDOW_S`), parent or subagent | `held_live` | Skipped by the model loop; stays pending. Derivation has no guard |
| On-disk cache gated by `valid_entry` | `call_cached` | Valid cached output reused, not re-called; a rejected output is logged and left uncached — **paid again every night** while it keeps failing; a poisoned cache file is overwritten on the retry |
| `status_narrative` keyed on `(ledger_hash, prompt_version, model)` | `refresh_narratives` | Narrative re-called only when the ledger, ADR headers or prompt change |
| `blobs` content-addressed, `INSERT OR IGNORE`; `backstop_state` last-seen hash/sha | `store_blob`, `capture_backstop` | Unchanged config and repos produce no rows; git capture is incremental |
| `breakage` open-row dedup | `check_drift` | One open row per (condition, old_version, new_version) — condition 1 also per key; keys added under one version pair are one row (#30). An open row is never re-raised, nor its notification |
| One cross-check row per local day, open or acknowledged | `cross_check` | A day is judged once, ever |
| `PRAGMA user_version` | `init_db` | Each migration fires exactly once per DB |

Replaced wholesale each run: `sunk_cost`. Appended: `raw_records`, `change_events`, `blobs`, `breakage`. Re-derived per session: `records_index`, `usage`, `tool_events`, `command_grains`, `field_histogram`. Upserted: `audit`, `status_narrative`, `backstop_state`, `health`, `project_presence` (a history; rows update in place, never deleted — ADR-0018). Deleted by compaction: a session's raw records and work-dir files once its newest record is `HINDSIGHT_RAW_DAYS` old and nothing holds it (ADR-0034).

**Not idempotent:** the listener. `otel_events` and `otel_metrics` have only an autoincrement id, so a re-sent OTLP batch is stored twice; this relies on Claude Code not retrying a `200`.

### Job order, every run

sweep → project bookkeeping → derivation → drift guard and cross-check (skipped if derivation failed or any session is still due) → what-pass → how narrative (skipped if the what-pass paused) → backstop → sunk-cost scan → compaction → `health` row (`source=analysis`). Each job runs in its own try block; a failure is one `<job> failed:` stderr line and lands in the health row (ADR-0038).

### The first run after a schema bump (v10–v13)

`init_db` runs migrations before anything else. v10 (ADR-0031, ADR-0039) is additive and ends with `auto_vacuum = INCREMENTAL` and a full `VACUUM`; v11 drops `audit.date`; v12 drops `scan_runs`; v13 redacts the stored backstop blobs and runs a full `VACUUM` (about 6 s on a 1.1 GB store), retried at the next open if the store is busy. **No model calls**; audit rows and caches are untouched. Whichever process calls `init_db` first with the new code does this — the async capture hook included, so the `VACUUM` can run inside a hook firing. The listener runs only its own `CREATE IF NOT EXISTS`; `serve.py` and the health hook open read-only and never migrate. Re-derivation is no longer a schema bump: a deriver version bump clears its `deriver_state` and the next run rebuilds every session with raw records.

### The drift guard, every run

`check_drift` runs after derivation only when no session is due (ADR-0038 §3) and never halts the run — a guard exception is `drift guard failed:` and the run continues (#15, ADR-0020, ADR-0037). Conditions: 1 thinned key (*problem*), 2 added keys (*informational*), 4 the OTel/transcript cross-check (*problem*); 5 unparseable record (written by derivation) and 6 rewritten prefix (written by capture). Condition 3 is retired (ADR-0037 §6). Every open row is a banner on every view; conditions 1 and 4 also pop a macOS notification. `acknowledge-breakage <id>` closes the row; its `new_version` becomes the comparison baseline. It never rescans: a parser fix is a deriver version bump, which re-derives through the mechanism above.

## Internal-call authentication

None present. The nightly job calls no HTTP endpoint. The OTel exporter → listener POST (`http://127.0.0.1:4318/v1/logs`, `/v1/metrics`) carries no token. The listener checks three things: `Host` must name loopback (`403` otherwise — the DNS-rebinding guard, `home.loopback_host`); `Content-Type` must start with `application/json` (`415` otherwise — a browser cannot send that cross-origin without a preflight, and there is no `OPTIONS` handler, so a web page the operator visits cannot post rows), and the body must stay under `MAX_BODY` 8 MiB declared, chunked or inflated. No auth beyond that; the protection is the loopback bind (see [flows.md](flows.md)). Any local process sending JSON can write rows into `otel_events`. The hooks and the nightly reach SQLite by filesystem permission only; the health hook runs `launchctl print`/`kickstart -k` as the user; `serve.py` answers a loopback GET only when its `Host` names loopback (`403` otherwise).

## Where to see last runs

- Nightly: `<home>/logs/analyze.log` — one `claude --version:` line per run, `rejected <file>: '<80 chars>'` for gated-out model output, `model call exited N: <200 chars>`, `model call timed out after 300s`, `claude CLI not found on PATH — model calls paused this run`, `<job> failed: …`, `compaction: N session(s) compacted, M held`, `analysis run already in progress; exiting`. The job appends (`--log`, `home.log_to`, which recreates `<home>/logs/` if it was deleted); the file is never rotated.
- Listener: `<home>/logs/listener.log` — startup line, `refused 415|413`, `ingest error on <path>:`, `<path>: skipped N row(s)`. The request log is silenced; never request bodies.
- Capture hook: **no log.** Errors land only in the `health` row (`source=capture`).
- `health` table: `last_success`, `last_error`, `error_text`, `failing_since` for `capture`, `listener`, `analysis`. The health hook shows a failing source, a missing job or "capture behind OTel" as a `systemMessage` at session start, silent when healthy.
- In the product: every view's header carries the open breakage banner(s) with the acknowledge command; `/what` and `/how` state `synced through <date>` (`/what` adds the session count). `/how`'s coverage line is the cheapest "did last night run" check.
- `launchctl print gui/$(id -u)/<label>` for last exit status and whether the job is loaded.

## Concurrency between the writers and the server

The file is in WAL mode (issue #12): every writer's `init_db` sets the pragma, and it persists in the file. Readers never wait on a writer, and a page held open in `serve.py` never blocks a commit. Three writers serialise against each other: the capture hook (`BEGIN IMMEDIATE`, 30 s connect timeout), `analyze.py` (30 s), and the listener (`busy_timeout` 5 s per request). The nightly commits per session in derivation and holds no transaction across a model call. Long single writes that can starve a listener insert past 5 s: `capture_backstop` holds one transaction across every repo's `git log`/`show`; the v10 `VACUUM` is exclusive over the whole file. The readers (`serve.py`, `how.py`) open `mode=ro` with a 30 s timeout; the health hook with 1 s.
