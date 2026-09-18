# Permissions

## Principals

There are no roles, claims, tokens, cookies or logins. One macOS user owns the repo, `local-data/` and the loopback interface, and every request to either server is served as that operator (ADR-0001). The real "roles" are the processes, which differ in what they may touch:

| Process | Entry | DB access | Other reach |
| --- | --- | --- | --- |
| Analysis run | `analyze.py` — nightly launchd job or foreground; `attribute`, `acknowledge-breakage` subcommands | Read-write, every table except `otel_*` | Reads transcripts, `~/.claude`, workspace repos; runs `claude -p`, `git`, `osascript` |
| Backfill importer | `import_backfill.py` | Writes `sessions`, `audit` only; never touches an existing id | Reads `local-data/backfill/` |
| Server | `serve.py` on `127.0.0.1:8321` | Read-only (`mode=ro`) | Reads `.claude/my-process.md` of the `?p=` project, `design/tokens.css`, `build/assets/*` |
| Listener | `listener.py` on `127.0.0.1:4318`, the one background process | Writes `otel_events`, `otel_metrics` only | — |
| Hook | `hook.py`, spawned by Claude Code per hook event | None — POSTs one OTLP record to the listener | `stat` of the session's `cwd` at SessionStart (ADR-0018) |
| Model | `claude -p` subprocess of the analysis run | None — its stdout is data, gated before write | Receives the extract (tool results excluded, ADR-0002) and the run ledger |
| Git pre-commit hook | `.githooks/pre-commit`, opt-in per clone via `git config core.hooksPath .githooks` | — | Refuses staged additions matching `.githooks/denylist.txt` |
| Public repo reader | Anyone on GitHub | None | Everything in git history; never `local-data/` |

**Scope is derived from nothing.** Loopback is the credential. The two request-scoped inputs are `?p=` (how view), checked by `declaring_projects()` against DB project names that have a declaration file — an unknown value says so and falls back to the busiest — and the `/what#<session-id>` anchor (ADR-0023), a client-side fragment that opens a rendered row and never reaches a query.

## Resource × operation × process

| Resource | Read by | Written by |
| --- | --- | --- |
| `otel_events` | Server (where view, `excluded_sessions` filtered); analysis run (hook folder identity) | Listener, any local POST |
| `otel_metrics` | Nothing serves it | Listener |
| `sessions`, `audit`, `excluded_sessions`, `project_presence`, `status_narrative`, `sunk_cost` | Server | Analysis run; importer for `sessions`/`audit` |
| `tool_events` (incl. `error_text`), `usage`, `command_grains`, `subagent_transcripts` | Server | Analysis run's substrate scan, per session wipe-and-refill (ADR-0019) |
| `field_histogram`, `scan_runs` | Analysis run (drift guard, ADR-0020) | Analysis run |
| `breakage` | Server (open rows → banner on every view) | Analysis run opens; `acknowledge-breakage <id>` closes, never rescans |
| `blobs`, `change_events`, `backstop_state` | Nothing serves them | Analysis run's backstop |
| `~/.claude/projects/**/*.jsonl`, `…/subagents/agent-*.jsonl` | Analysis run | Never — no delete path exists |
| `~/.claude/{CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json}`, `plugins/installed_plugins.json` | Analysis run, copied verbatim into `blobs` | Never |
| Skill and command bodies, MCP config, CLAUDE.md chain (user scope and per project) | Analysis run (`sunk_cost`) | Never |
| Workspace repos `~/Documents/Claude/*` | Analysis run: `git log`/`git show` of `.claude/` commits into `blobs`; server: `.claude/my-process.md` only | Never |
| `local-data/` (DB, extracts, model cache, backfill) | Analysis run, server, importer | Analysis run, listener; gitignored |
| `~/Library/LaunchAgents/com.hindsight.*.plist`, `~/Library/Logs/hindsight/` | launchd | `install` / `uninstall` of listener and analysis run |

No row-level security: SQLite has none and there is one owner.

## Guards, and what enforces them

| Guard | Enforced by |
| --- | --- |
| Both servers reachable only from this Mac | Socket bind to `127.0.0.1` (`listener.make_server`, `serve.make_server`) |
| The server cannot write | SQLite URI `file:…?mode=ro` (`serve.open_db`; `how.py`'s smoke entry likewise) |
| A page render never blocks a nightly or listener commit, and vice versa | `PRAGMA journal_mode=WAL`, persisted in the file by whichever writer opens first; 30 s connect timeout; listener `busy_timeout` 5 s |
| Only three routes | Code: `VIEWS` allowlist, anything else 404; `/` redirects to `/what` |
| Hindsight's own `claude -p` sessions never enter the inventory | Code: prompt signature (`ANALYSIS_SIGS`) at sync → `excluded_sessions`; the server filters `otel_events` by it; a subagent of an excluded parent inherits the exclusion (ADR-0019) |
| A transcript still being written is not scanned, extracted, wiped for growth or attributed | Code: `substrate._is_live` — any mtime within `LIVE_WINDOW_S` (300 s), the parent's or any of its subagent transcripts' |
| Transcript content boundary | Code and ADR: the extract excludes tool results (ADR-0002); the only tool-result content stored is a failed call's text, `tool_events.error_text` (ADR-0027 §2); nothing of a successful call; the error line is the first and only transcript text the UI renders |
| Model output written only when well-formed | Code: `valid_entry` for audit entries, `score.contract` for the status narrative — at write time, never on page load |
| Home paths, key shapes, transcript filenames never committed | `.githooks/pre-commit` over the denylist — opt-in per clone, cannot read a PNG |
| Real data never in git | `.gitignore`: `local-data/`, `*.png` except `docs/screenshots/`, `settings.local.json`, `.claude/skills/` |

## Where a check is missing, and whether it matters

| Gap | Fact | Consequence |
| --- | --- | --- |
| Listener accepts any local JSON writer | No auth; `Content-Type` must start with `application/json` (`415`) and the body is capped at `MAX_BODY` 8 MiB (`413`, or dropped once chunked/inflated), so a web page's cross-origin simple POST is refused (#34); unknown paths still return 200 (`Handler.do_POST`) | Any local process can pollute `otel_events`; on a single-user Mac the writer set is the operator's own processes |
| Server has no auth | `serve.py` serves every view to any loopback client | Session titles, model prose, project and consumer names, and — since ADR-0027 — verbatim, uncapped error text including tracebacks that carry paths on every frame. Not `blobs`. |
| `blobs` holds config verbatim | `capture_backstop` snapshots the whole `BACKSTOP_SURFACE` file and every `.claude/` commit's before/after | Reading the DB file reveals every settings/MCP file, current and historical; protected only by the file's Unix mode and the gitignore. See [variables.md](variables.md). |
| Model output gated by shape, not content | `valid_entry`, `score.contract` | A well-formed but wrong entry is written; `eval/` is the standing check. See [automation.md](automation.md). |
| Pre-commit hook is opt-in | A clone without `core.hooksPath` set has no denylist | The publication rule then rests on the author alone |
| `attribute` trusts the operator | Refuses only on a missing DB, an unreadable folder or a bad instant | A wrong `<synced-name> <folder>` pairing stamps the wrong identity; the next run re-keys those sessions under it |
