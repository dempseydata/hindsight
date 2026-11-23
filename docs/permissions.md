# Permissions

## Principals

There are no roles, claims, tokens, cookies or logins. One macOS user owns the repo, Hindsight home (`~/.hindsight/` or `$HINDSIGHT_HOME`), `local-data/` and the loopback interface, and every request to either server is served as that operator (ADR-0001). The real "roles" are the processes, which differ in what they may touch (runtime steps in [flows.md](flows.md)):

| Process | Entry | DB access | Other reach |
| --- | --- | --- | --- |
| Analysis run (F3) | `analyze.py` — nightly launchd job or foreground; single-flight by `flock` on `<db dir>/analysis.lock` | Read-write, every table except `otel_*` (reads those); deletes raw records at compaction | Reads transcripts, `~/.claude`, workspace repos; runs `claude -p`, `git`, `osascript`, `extract.py` |
| Operator write commands (F5) | `analyze.py attribute`, `acknowledge-breakage`; `import_backfill.py` — none takes the flock | `sessions`, `project_presence`, `breakage`; importer `sessions`, `audit` only, never an existing id | Importer reads `local-data/backfill/`; `attribute` stats a workspace folder |
| Capture hook (F2) | `capture.py`, spawned async by Claude Code at SessionStart / Stop / SubagentStop (the plugin's `hooks/hooks.json`) | Writes `raw_records`, `transcripts`, `breakage` (condition 6), `health`; creates and migrates the db if needed | Reads any `.jsonl` path named in the payload; `stat` of the session's `cwd` (ADR-0018) |
| Health hook (F6) | `health.py`, synchronous at SessionStart, 5 s | Read-only (`mode=ro`, path quoted) | Re-points `<home>/current`; `launchctl print` and `kickstart -k` of the listener |
| Server (F4) | `serve.py` on `127.0.0.1:8321` | Read-only (`mode=ro`, path quoted) | Reads every DB project's `local-process.md`, the house master named in `~/.claude/CLAUDE.md`, the chosen project's `docs/adr/*.md` (and runs `git log` on them), `design/tokens.css`, `cli/assets/*` |
| Listener (F1) | `listener.py` on `127.0.0.1:4318`, the one background process | Writes `otel_events`, `otel_metrics`, `health` only; creates the db file if absent | — |
| Ops command (F5) | `hindsight.py`, run by the user-invoked `/hindsight:ops` skill (`disable-model-invocation`) | None — `install --from` moves a v1 database file into Hindsight home, once, after booting out both jobs; nothing deletes it | Writes both plists and `<home>/current`, runs `launchctl`, starts `serve.py` detached; reads `~/.claude/settings.json` to list v1 hook entries, never writes it; `GET /` on the views server |
| Model | `claude -p` subprocess of the analysis run: `--tools ""`, `--strict-mcp-config`, hooks disabled, a fixed empty cwd | None — its stdout is data, gated before write | Receives the extract (tool results excluded, ADR-0002) and the run ledger + ADR headers; its own transcript lands under `~/.claude/projects/` and is captured |
| Git pre-commit hook | `.githooks/pre-commit`, opt-in per clone via `git config core.hooksPath .githooks` | — | Runs `claude plugin validate`; refuses staged additions matching `.githooks/denylist.txt` or the private-name list kept outside the repo |
| Public repo reader | Anyone on GitHub | None | Everything in git history; never `local-data/` |

**Scope is derived from nothing.** Loopback is the credential. The two request-scoped inputs are `?p=` (how view), checked by `declaring_projects()` against DB project names whose process resolves (ADR-0032) — an unknown value says so and falls back to the busiest — and the `/what#<session-id>` anchor (ADR-0023), a client-side fragment that opens a rendered row and never reaches a query. The capture hook trusts its payload for the transcript path.

## Resource × operation × process

| Resource | Read by | Written by |
| --- | --- | --- |
| `raw_records`, `transcripts` (raw store, ADR-0031) | Analysis run (bookkeeping, derivation, extract); health hook (capture-behind) | Capture hook and the run's sweep; compaction deletes `raw_records` (registry rows stay) |
| `otel_events` | Server (where view, `excluded_sessions` filtered); analysis run (OTel histogram, cross-check); health hook | Listener, any local POST |
| `otel_metrics` | Nothing serves it | Listener |
| `health` | Health hook | Listener, capture hook, analysis run — one row each |
| `sessions`, `audit`, `excluded_sessions`, `project_presence`, `status_narrative`, `sunk_cost` | Server | Analysis run; `attribute` for identity and presence; importer for `sessions`/`audit` |
| `records_index`, `tool_events` (incl. `error_text`), `usage`, `command_grains`, `deriver_state` | Server (not `deriver_state`) | Analysis run's derivers, per session wipe-and-refill of `raw` rows; compaction relabels them `compacted` |
| `field_histogram`, `otel_histogram` | Analysis run (drift guard, ADR-0037) | Analysis run |
| `breakage` | Server (open rows → banner on every view) | Analysis run (conditions 1, 2, 4, 5), capture hook (6); `acknowledge-breakage <id>` closes, never rescans |
| `blobs`, `change_events`, `backstop_state` | Nothing serves them | Analysis run's backstop |
| `~/.claude/projects/**/*.jsonl`, `…/subagents/agent-*.jsonl` | Analysis run (sweep), capture hook | Never by hindsight — no delete path exists; the model child adds its own transcript via Claude Code |
| Any other `.jsonl` path named in a hook payload | Capture hook | Never |
| `~/.claude/{CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json}`, `plugins/installed_plugins.json` | Analysis run, copied verbatim into `blobs`; server (`CLAUDE.md`, for the house-master pointer); ops command (`settings.json`) | Never |
| Skill and command bodies, MCP config, CLAUDE.md chain (user scope and per project), `~/.claude.json` | Analysis run (`sunk_cost`) | Never |
| Workspace repos `~/Documents/Claude/*` | Analysis run: `git log`/`git show` of `.claude/` commits into `blobs`, `local-process.md`, ADR headers; server: `local-process.md`, `docs/adr/*.md`, `git log` | Never |
| Hindsight home (`hindsight.db`, `analysis.lock`, `logs/`, `current`) | Every process; launchd through `current` | DB as above; each job appends to its log; ops command (`current`, `logs/`, the `--from` move); health hook (`current`). Nothing deletes the home or the db |
| Analysis work dir (extracts, model cache): `$CLAUDE_PLUGIN_DATA/analysis`, else `local-data/analysis` | Analysis run | Analysis run; growth and compaction unlink per-session files |
| `local-data/` (backfill, eval material, a working-copy work dir) | Importer, analysis run, `eval/` | Analysis run, `eval/`; gitignored |
| `~/Library/LaunchAgents/com.hindsight.*.plist` | launchd | `/hindsight:ops install` / `uninstall` |
| launchd jobs `gui/<uid>/com.hindsight.{ingest,nightly}` | Health hook (`print`) | Ops command (`bootstrap`/`bootout`); health hook (`kickstart -k` ingest) |

No row-level security: SQLite has none and there is one owner.

## Guards, and what enforces them

| Guard | Enforced by |
| --- | --- |
| Both servers reachable only from this Mac | Socket bind to `127.0.0.1` (`listener.make_server`, `serve.make_server`). Neither checks `Host`, so loopback is not the same as same-machine *origin* (F1, F4) |
| A cross-site page cannot post to the listener | `Content-Type` must start `application/json` (`415`) and there is no OPTIONS handler, so no preflight succeeds (#34). A DNS-rebinding page is same-origin, so `Host` must also name loopback (`403`, `home.loopback_host`) |
| Bounded listener bodies | `MAX_BODY` 8 MiB on declared, chunked and inflated length (`413` or dropped) — except a negative chunk size (F1 step 2) |
| The server and health hook cannot write | SQLite URI `file:…?mode=ro` (`serve.open_db`, `health.check`; `how.py`'s smoke entry likewise), each with the path URL-quoted |
| A page render never blocks a run, capture or listener commit, and vice versa | `PRAGMA journal_mode=WAL`, persisted in the file by whichever writer opens first; 30 s connect timeout; listener `busy_timeout` 5 s; capture's `BEGIN IMMEDIATE` |
| One analysis run at a time | `fcntl.flock` on `<db dir>/analysis.lock`, released with the process (ADR-0038). Capture, listener and the F5 write commands do not take it |
| Only three routes, GET only | Code: `VIEWS` allowlist, anything else 404; `/` redirects to `/what`; only `do_GET` defined, other methods 501 |
| Hindsight's own `claude -p` sessions never enter the inventory | Code: prompt signature (`ANALYSIS_SIGS`) at sync → `excluded_sessions`; the server filters `otel_events` by it; a subagent of an excluded parent inherits the exclusion (ADR-0019). Their raw records are still captured and compacted |
| The model child cannot act on the machine | `claude` flags: `--tools ""`, `--strict-mcp-config`, `disableAllHooks`, fixed empty cwd (`analyze.MODEL_FLAGS`, `MODEL_CWD`) |
| A session still being written is not extracted or invalidated for growth | Code: `held_live` (newest raw record captured < 300 s ago) for the what-pass; `substrate._is_live` (transcript mtime, parent or any subagent) for growth. Derivation has no live guard |
| Captured history is never silently rewritten | Code: SHA-256 of the last captured line re-checked before every append; a mismatch writes condition 6 and appends nothing (ADR-0033) |
| Transcript content boundary | Code and ADR: the extract excludes tool results (ADR-0002); the only tool-result content stored in derived tables is a failed call's text, `tool_events.error_text` (ADR-0027 §2); the error line is the first and only transcript text the UI renders. The raw store holds whole lines until compaction |
| Model output written only when well-formed | Code: `valid_entry` for audit entries, `contract_v2` for the status narrative — at write time, never on page load |
| Deletion fails closed | Code: `raw_days()` raises on a negative or non-numeric `HINDSIGHT_RAW_DAYS`, deleting nothing; compaction holds pending/partial sessions, open rewrite breakages and any session a deriver still has due (ADR-0034) |
| Ops never destroy the store | Code: `install --from` refuses over an existing db; uninstall never deletes the db or logs; v1 logs never move over an existing file; health's repoint refuses a real `current` directory |
| Home paths, key shapes, transcript filenames, private project names never committed | `.githooks/pre-commit` over the denylist and the private list — opt-in per clone, cannot read a PNG |
| Real data never in git | `.gitignore`: `local-data/`, `*.png` except `docs/screenshots/`, `.claude/`, `.env*`, `*.log` |

## Where a check is missing, and whether it matters

| Gap | Fact | Consequence |
| --- | --- | --- |
| Listener accepts any local writer | No auth; unknown paths still return 200 and record a health success (`Handler.do_POST`) | Any local process can forge `otel_events` — which take precedence over transcript usage in the where view, feed the cross-check and the health check's capture-behind line (F1) |
| Negative chunk size bypasses the body cap | `int(size, 16)` accepts `-N`; `rfile.read(-N)` reads to EOF (`listener.py:149-155`) | A local client can push an uncapped body into memory and hold a handler thread until it closes the connection |
| Server has no auth | `serve.py` serves every view to any local client; a non-loopback `Host` (a DNS-rebinding page) gets `403` (F4) | Session titles, model prose, project and consumer names, and — since ADR-0027 — verbatim, uncapped error text including tracebacks that carry paths on every frame. Not `blobs`, not raw records |
| Capture reads any `.jsonl` path | `capture.is_transcript` checks the suffix only; ids come from the path stem | Whoever controls a hook payload can have any readable `.jsonl` file stored verbatim and synced as a session; the stem reaches `data-id` unescaped in `what.js:33` |
| Write commands bypass single-flight | Capture, listener, `attribute`, `acknowledge-breakage`, `import_backfill` call `init_db` without the flock | They interleave with a run, serialised only by SQLite's write lock; a first capture after an upgrade can run a pending migration (including v10's `VACUUM`) inside a hook |
| File modes come from the umask | No `chmod` in `cli/`; logs are opened `0644` (`home.log_to`) | DB, logs, plists and caches are typically world-readable files; isolation from other local users rests on the home directory's mode |
| `blobs` holds config verbatim | `capture_backstop` snapshots the whole `BACKSTOP_SURFACE` file and every `.claude/` commit's before/after | Reading the DB file reveals every settings/MCP file, current and historical; protected only by the file's Unix mode; it lives in Hindsight home, outside the repo. See [variables.md](variables.md). |
| Model input is not redacted | ADR-0034 rejects a redaction pass | Secrets typed into a conversation reach the model in the extract, and sit in the raw store until compaction |
| No in-code spend cap | Serial calls; only the `"limit"` stderr sniff and `claude` missing pause the what-pass | The first run is a full-history backfill bounded by subscription limits alone |
| Model output gated by shape, not content | `valid_entry`, `contract_v2` | A well-formed but wrong entry is written; `eval/` is the standing check. See [automation.md](automation.md). |
| Port squatting on 8321 | `hindsight.http_up` treats any HTTP answer as the views server | `/hindsight:ops open` sends the browser to whatever answers |
| Pre-commit hook is opt-in | A clone without `core.hooksPath` set has no denylist | The publication rule then rests on the author alone |
| `attribute` trusts the operator | Refuses only on a missing DB, a folder not there or outside the workspace root, or a bad instant | A wrong `<synced-name> <folder>` pairing stamps the wrong identity; the next run re-keys those sessions under it |
