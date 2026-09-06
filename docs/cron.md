# Scheduled and background work

Two launchd user agents. There is no other background process (ADR-0001).

| Job | Label | Schedule | Program | Log | Limits / retry |
| --- | --- | --- | --- | --- | --- |
| Ingest listener | `com.hindsight.ingest` | `RunAtLoad` + `KeepAlive` — always up, restarted by launchd on exit | `<sys.executable> build/listener.py` (no args → port 4318, default DB) | `local-data/listener.log` (stdout+stderr) | `busy_timeout` 5 s per request; no body cap; no retry (client is told `200`) |
| Nightly analysis | `com.hindsight.nightly` | `StartCalendarInterval` 03:00 local | `<sys.executable> build/analyze.py` with `PATH` from the installing shell | `local-data/analyze.log` | Serial model calls, 300 s each; stops on `LimitExhausted` (rate limit or missing `claude`) and resumes next night |

Install / remove: `python3 build/listener.py install|uninstall`, `python3 build/analyze.py install|uninstall`
(`listener.py:206-224`, `analyze.py:990-1005`). Both do `launchctl bootout` (ignored on failure) then
`bootstrap gui/<uid>`. Inspect with `launchctl print gui/$(id -u)/com.hindsight.ingest`.

## Idempotency of the nightly run

A second run over unchanged input does no model calls and no duplicate writes:

| Mechanism | Where | Effect |
| --- | --- | --- |
| `sessions.status` + `SELECTABLE` | `analyze.py:262, 934` | `done`, `empty`, `lost` sessions are never reprocessed |
| `audited_size` watermark + `REAUDIT_SHARE = 0.25` | `analyze.py:484, 526-533` | A grown transcript is re-audited only when growth ≥ 25 %; imported sessions keep `NULL` and are never re-audited on size |
| `skipped_records IS NULL` | `substrate.py` | Substrate scan runs once per session |
| Live-session guard (mtime < 300 s) | `substrate.py:237-245` | In-flight transcripts skipped by every stage |
| On-disk cache passing `valid_entry` | `analyze.py:613-615` | A cached model output is reused, not re-called; a poisoned cache file is overwritten on retry |
| `status_narrative` hash | `analyze.py:724-727` | Narrative re-called only when `(project, ledger_hash, prompt_version, model)` changes |
| `blobs` content-addressed, `INSERT OR IGNORE` | `analyze.py:770` | Unchanged config produces no new rows |
| `backstop_state` last-seen sha per repo | `analyze.py:808` | Git capture is incremental |
| `PRAGMA user_version` | `analyze.py:298-356` | Migrations fire once |

Replaced wholesale each run: `sunk_cost`, `project_presence`. Appended: substrate tables,
`change_events`, `blobs`, `excluded_sessions`. Upserted: `audit`, `status_narrative`, `backstop_state`.

## Internal-call authentication

None needed and none present: the nightly job calls no HTTP endpoint. The hook → listener call
is loopback with no token (see [flows.md](flows.md) F2).

## Where to see last runs

- Listener: `local-data/listener.log` — startup lines, exception strings, skip counts, and socketserver tracebacks (a `BrokenPipeError` is in the current log).
- Nightly: `local-data/analyze.log` — full run output; `rejected <file>: '<80 chars>'` lines mark gated-out model output.
- In the product: the `/what` header's "synced through <date> · N sessions" line (`serve.py:545, 575`).

## Concurrency between the two jobs and the server

Both writers and the reader open the same file with no WAL mode. A long `analyze.py` transaction
can block a `serve.py` request into a 500 and can push a listener insert past its 5 s
`busy_timeout` into a silently dropped batch. Nothing corrupts; data can be lost on the ingest side.
