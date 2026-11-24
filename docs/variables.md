# Variables, paths and secrets

Hindsight reads **five** environment variables of its own or its host's (`HINDSIGHT_HOME`, `HINDSIGHT_TZ`, `HINDSIGHT_RAW_DAYS`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PLUGIN_ROOT`), relies on `PATH` to find `claude`, and has no config file of its own.
Everything else is a hard-coded constant or a CLI flag. The secret surface is not "which env vars
leak" but "which files get copied into the DB" — and, since a push to this repo is a deploy, "what
must never be committed".

## Configuration

Scope: **server** = the Python processes (capture and health hooks, listener, analysis run, serve); **client** = the browser.
Rotation "re-install" means re-running `/hindsight:ops install`, which rewrites both plists.

| Name | Used by | Scope | Source | Rotation | Risk |
| --- | --- | --- | --- | --- | --- |
| `HINDSIGHT_HOME` | `home.home()` — the DB default, the logs, `current`, the lock | server | env path; unset = `~/.hindsight`; baked into both plists at install if set | re-install | The `--db` defaults read it once at import; the capture and health hooks read it from Claude Code's env and take no `--db`. If the shell, the plists and Claude Code disagree, writes split across two databases |
| `HINDSIGHT_TZ` | `analyze.apply_tz` at import — so serve, how, import_backfill too | server | env, IANA name; unset = host zone; baked into the nightly plist at install | re-install | Low — moves every day bucket. Sets process-global `TZ`, which the `claude -p` child inherits. A bad name is one stderr line and the host zone |
| `HINDSIGHT_RAW_DAYS` | `analyze.raw_days` → `compact` (ADR-0034) | server | env, whole days; unset = `90`; `0` = never compact | re-install — baked into the nightly plist at install if set | **Destructive.** Lowering it deletes raw records at the next run, no confirmation. A negative or non-numeric value errors the compaction job and compacts nothing. A value changed in the shell reaches the 03:00 job only after `/hindsight:ops install` is re-run; older plists compact at 90 until then |
| `CLAUDE_PLUGIN_DATA` | `analyze.DEFAULT_WORK_DIR` | server | env, set by Claude Code for the plugin (passed through by the `ops` skill); baked into the nightly plist at install if set | re-install | Unset, the work dir is `<plugin root>/local-data/analysis`, which a plugin update sweeps — cached model outputs are lost and paid for again. `install` warns |
| `CLAUDE_PLUGIN_ROOT` | `hooks/hooks.json`, `skills/ops/SKILL.md`, `health.py` | server | set by Claude Code per plugin version | changes with each update | The health hook re-points `<home>/current` to it and kickstarts the listener |
| `PATH` | `hindsight.plists`; `default_model_runner` resolves `claude` on it | server | installing shell's `PATH`, baked into the nightly plist | re-install | `claude` must resolve on it or every run pauses model work (`LimitExhausted`) |
| `TMPDIR` | `analyze.MODEL_CWD` via `tempfile.gettempdir()` | server | env | — | None — locates the empty model working dir |
| Listener port | `listener.py` `DEFAULT_PORT`, `--port` | server | constant `4318`; the plist passes no `--port`, and `install` cannot set one | — | Must match the operator's `OTEL_EXPORTER_OTLP_ENDPOINT`; a mismatch is silent telemetry loss |
| Body cap | `listener.py` `MAX_BODY` | server | constant `8 MiB`: declared `Content-Length` over it is `413`; chunked or inflated gzip over it is a failed body (`200` + `partialSuccess`) (#34) | — | Low — a real batch is far smaller; an over-cap body is one stderr line and nothing stored |
| Serve port | `serve.py` `DEFAULT_PORT`, `--port`; `hindsight.SERVE_PORT` | server | constant `8321`; binds `127.0.0.1` only. `/hindsight:ops serve|open` hardcode it — `--port` works only when `serve.py` is run directly | — | Low |
| DB path | analyze, listener, serve, import_backfill — `--db` (`how.py`'s smoke run uses the default) | server | `<home>/hindsight.db` (+ `-wal`, `-shm`) | — | **Holds copied-in secrets** (below). `--db` on analyze also moves the lock; it never moves the hooks' DB |
| Lock | `run_analysis` | server | `<db dir>/analysis.lock` — `flock`, non-blocking (ADR-0038) | — | None — empty file |
| Transcript root | `analyze.py --root` | server | `~/.claude/projects` | — | Personal data source; the sweep captures everything under it |
| Claude dir | `analyze.py --claude-dir` | server | `~/.claude`; reads `BACKSTOP_SURFACE` (`CLAUDE.md`, `settings.json`, `settings.local.json`, `keybindings.json`, `mcp.json`) + `plugins/installed_plugins.json` | — | Config with possible tokens |
| Projects dir | `analyze.py`, `analyze.py attribute`, `serve.py` — `--projects-dir` | server | `~/Documents/Claude` (the author's layout); every child with `.git` has its `.claude/` history captured; ADR headers read from `<project>/docs/adr`; also the prefix stripped from transcript dir names to get project names | — | `install` never passes it, so the nightly always uses the default; another layout gets no how-view or narrative and unstripped project names. Analyze and serve must be given the same value |
| Process declaration | `how.resolve_declaration` (ADR-0032) | server | `<project>/local-process.md`, else the house master named under `## Process` in `~/.claude/CLAUDE.md` | — | `.claude/my-process.md` is never read |
| Work dir | `analyze.py --work-dir` | server | `$CLAUDE_PLUGIN_DATA/analysis`, else `<plugin root>/local-data/analysis` (`extracts/`, `what-v3/`) | — | Plain-text extracts and raw model output; deleted per session at compaction |
| Backfill dir | `import_backfill.py --backfill-dir` | server | `<repo>/local-data/backfill` | — | Same |
| Model pin | `analyze.MODEL` (what, merge and status passes; stamped on every `audit`/narrative row); `"model"` in `eval/what_cases.json`, `eval/status_v2_cases.json`, `eval/cases.json` | server | constant `claude-haiku-4-5-20251001` in **four places** | change all together, run the evals first | `run_v2.py` asserts its manifest equals `analyze.MODEL`; `what_run.py` uses `analyze.MODEL` directly (its manifest string is a label); `run.py` (v1) uses `cases.json`'s own. Nothing else enforces the gate |
| Prompt versions | `analyze.PROMPT_VERSION` `what-v3`, `STATUS_VERSION` `status-v2`; `merge-v1.txt` | server | constants → `cli/prompts/<v>.txt` | — | Recorded on every row; the what cache dir is keyed by version. The merge prompt is not versioned on the row |
| Schema version | `analyze.init_db` `PRAGMA user_version` | server | `13` (v10 additive v2 core, v11 drops `audit.date`, v12 drops `scan_runs`, v13 redacts stored blobs and `VACUUM`s) | — | A downgrade is not supported. Any process that calls `init_db` — the capture hook included — can fire a pending migration |
| `claude -p` timeout | `analyze.CALL_TIMEOUT`; `eval/run.py` literal | server | `300` s per call | — | The only per-call bound; no per-run cap |
| Model flags | `analyze.MODEL_FLAGS`, `MODEL_CWD` | server | `--tools "" --strict-mcp-config --settings {"disableAllHooks": true}`, cwd `$TMPDIR/hindsight-model-cwd` | — | See [automation.md](automation.md) |
| Subprocess timeouts | `claude --version`, `osascript` | server | `30` s; `git` calls have none | — | — |
| SQLite | analyze/listener DDL `timeout=30`; WAL; listener request `busy_timeout=5000`; serve/how `mode=ro` `timeout=30`; health `mode=ro` `timeout=1` | server | constants | — | — |
| Hook budgets | `capture.TIMEOUT`, `health.TIMEOUT`, `health.launchctl` | server | capture: `0.5` s stdin, `async`, no harness timeout set; health: `0.05` s stdin, `1` s per `launchctl` call, `1` s SQLite, `timeout: 5` in `hooks.json` | — | ADR-0036 budgets health at ~100 ms; nothing enforces it |
| `GRACE_S` | `health.py` | server | `120` s — "capture behind OTel" tolerance | — | — |
| Re-audit / live window | `analyze.REAUDIT_SHARE`, `substrate.LIVE_WINDOW_S` | server | `0.25`; `300` s | — | — |
| Nightly hour | `hindsight.NIGHTLY_HOUR` | server | `3` (03:00, `StartCalendarInterval`) | — | — |
| Tuning constants | `serve.CHIP_SHARE` `0.01`; `extract.PER_MSG_CAP` `1500`, `CHUNK_CAP` `180000`; what-eval pool 4 threads, `run.py` 6, `run_v2.py` serial | server | constants | — | Display and extraction only |
| `?p=` | `serve.py` how-view, `chrome.js` chips | client → server | URL query; an unknown project falls back to the busiest declaring one | — | Project names only |
| `theme` | `theme.js` | client | `localStorage`; `light` / `dark`, absent = system (ADR-0017) | toggle back to system removes it | None — one word, per browser |
| `filter` | `chrome.js`, `how.js` | client | `sessionStorage`, per tab: window preset, selected days, active chips, hide-cache-reads; dies with the tab | — | Project names only |
| `XDG_CONFIG_HOME` | `.githooks/pre-commit` | dev only | env; unset = `~/.config` | — | Only locates the private denylist |

## Outside the repo

| File | Content | Owner |
| --- | --- | --- |
| `~/.claude/settings.json` | Claude Code's OTEL exporter env pointing at `:4318` (README). The hooks ship in the plugin's `hooks/hooks.json`; v1's hand-wired hook entries, if still present, are for the operator to remove (`install` lists them, read-only) | Operator, by hand |
| `~/Library/LaunchAgents/com.hindsight.ingest.plist` | Absolute `sys.executable` + `<home>/current/cli/listener.py --log`; `RunAtLoad`, `KeepAlive`; `HINDSIGHT_HOME` if set | `/hindsight:ops install` |
| `~/Library/LaunchAgents/com.hindsight.nightly.plist` | Absolute `sys.executable` + `<home>/current/cli/analyze.py --log`; 03:00; `PATH` and, if set, `HINDSIGHT_HOME`, `HINDSIGHT_TZ`, `HINDSIGHT_RAW_DAYS`, `CLAUDE_PLUGIN_DATA` | `/hindsight:ops install` |
| `<home>/current` | Symlink to the live plugin root; both plists run through it | `install` (re-pointed), the health hook (re-pointed atomically on a plugin update), `uninstall` (removed) |
| `<home>/logs/{listener,analyze}.log` | Process logs, mode `0600`, never rotated. `analyze.log` carries the first 80 chars of any rejected model output and the first 200 chars of a failed call's stderr | The job itself (`--log`, `home.log_to`, which recreates `logs/`) |
| `<home>/logs/serve.log` | Request log of a views server started by `/hindsight:ops serve` or `open`, mode `0600` (tightened at each start), never rotated; a terminal-started one logs to its terminal. It is the **view-use record** (ticket 119): one stdlib line per request, local time without zone, path and full `?p=` query. Panel expansion is client-side `<details>` and is not recorded. Read with `grep '"GET '` | `hindsight.py` |
| `$TMPDIR/hindsight-model-cwd/` | Empty working dir for every `claude -p` call | `default_model_runner` |

Both plists pin the Python binary and `<home>/current` at install time; a plugin update is picked up by
the health hook re-pointing `current`, upgrading Python means re-install. The capture hook records the workspace folder's **inode**, never its path (ADR-0018).

## Secrets

Hindsight has none of its own — no API key (the model runs through the `claude` CLI's existing auth:
subscription login, or `ANTHROPIC_API_KEY` if the CLI is set up that way; Hindsight never reads it), no
tokens, no signing keys. What it has is **other people's secrets copied in**. No row is redacted, and
the DB and its sidecars are `0600` inside a `0700` Hindsight home (`home.private`), whatever the umask:

| Where | What | How | Exposure |
| --- | --- | --- | --- |
| `raw_records.line` | Every transcript line verbatim, zlib-compressed, kept `HINDSIGHT_RAW_DAYS` past the session's newest record | `capture.py`, the sweep | Anyone who can read `hindsight.db` |
| `blobs.content` | `~/.claude/{CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json}` and `installed_plugins.json`, current and every changed version since first run, **redacted** (`redact.py`): secret-named keys, `headers` values and known key shapes become `<redacted>`; a secret under an innocent name and in no known shape is not caught. Never compacted | `capture_backstop` | Same. **Never queried by `serve.py`** |
| `blobs.content` | Every committed version of every `.claude/*` file in every repo under the projects dir — `settings.local.json`, `.mcp.json` included if ever committed — redacted the same way | `_capture_project_git` | Same |
| `tool_events.error_text` | Verbatim, uncapped text of every failed tool result (ADR-0027): stderr, tracebacks, absolute paths, whatever a command printed | `substrate.py` deriver | **Served** in the where blob (`errs[].t`) |
| `otel_events.attributes` | Every OTLP attribute as JSON; whatever Claude Code exports — more with `OTEL_LOG_TOOL_DETAILS=1` | `listener.py` | Database |
| `audit.markdown`, `status_narrative` | Model-written prose derived from transcripts | analysis run | **Served** (what-view, how-view) |
| `<work dir>/extracts/`, `what-v3/` | Message text (1,500 chars per piece) and raw model output | `extract.py`, `analyze.py` | Filesystem, work dir `0700`; deleted per session at compaction |
| `<home>/logs/analyze.log` | Rejected-output heads, failed-call stderr heads | analysis run | Filesystem, `0600` |
| `local-data/eval/` | what-pass extracts (the regression set's real inputs), run outputs, the Stage B dry-run material (`so-what/`) | `eval/*.py` | Filesystem, untracked |

**Rotation:** if `hindsight.db`, a backup of `<home>` or `local-data/` is ever copied off the machine or committed, treat
every key in `~/.claude/settings*.json`, `~/.claude/mcp.json` and any workspace `.claude/settings.local.json`
/ `.mcp.json` as exposed and rotate — and treat the transcripts as disclosed. Redaction does not recall a copy already taken: a backup made before v13 (`hindsight.db.pre-v*` included) still holds config secrets.

**Client-side bundling:** each page inlines `tokens.css`, the view's JS, and JSON blobs as `const`s
(`<`-escaped against script breakout):
`DATA` (per-day token totals by project, chip names, hidden list, sync date), `WHAT` (audit rows:
session id, project, day, skip/ADR flags, and the model-written title and sections — prose derived
from transcripts), `WHERE` (tool, lens, session, subagent, model, latency, hook, retry, MCP-connection
rows; `errs` with the verbatim error text above; sunk-cost plugin and skill names with tokens; medians;
coverage). The how-view is server-rendered HTML with no blob. No key, token or path constant exists to
bundle; `error_text` is the one served field that can carry a path or a secret. `serve.py` has no auth, so any local process that can reach `127.0.0.1:8321` can read it; a non-loopback `Host` (DNS rebinding) is refused.

## Pre-go-live checklist

This repo is born public: every push is go-live. Before one:

- [ ] `git config core.hooksPath .githooks` is set in this clone — the pre-commit hook is opt-in per clone, runs `claude plugin validate`, and refuses staged additions matching `.githooks/denylist.txt` (home paths in `/Users/<name>` and dash-encoded form, `sk-ant-`, `ghp_`, `AKIA`, private-key headers, `<uuid>.jsonl`) or `~/.config/git/denylist-private.txt`. Extend the lists; never bypass them.
- [ ] `local-data/` is gitignored and absent from history; `hindsight.db` and its `.bak-*` copies never staged.
- [ ] `docs/screenshots/*.png` (the one un-ignored png path) were taken from a filtered or synthetic view — the where-view's error rows and the what-view's audit prose are transcript-derived.
- [ ] `eval/cases.json` and `eval/status_v2_cases.json` ledgers are committed in full by design (reviewed, ticket 087); `eval/what_cases.json` carries expectations only — its extracts stay under `local-data/eval/what/extracts/`. No so-what dry-run script exists under `eval/`; its material is untracked.
- [ ] Issue bodies and `background/` cite sessions by id, never by transcript text or home path.
- [ ] `security-preflight` run before any push touching `eval/`, `docs/screenshots/` or `background/`.
- [ ] `~/.claude/settings.json` OTEL env is documented as the reader's config to add, never shipped; the hooks ship in `hooks/hooks.json`.

Operator, on a machine that runs it:

- [ ] Run `/hindsight:ops install` from the shell holding the final `PATH`, `HINDSIGHT_HOME`, `HINDSIGHT_TZ`, `CLAUDE_PLUGIN_DATA`; re-run after changing any. `which claude` resolves on that `PATH`.
- [ ] Set `HINDSIGHT_RAW_DAYS` deliberately, then re-run `/hindsight:ops install` so the nightly plist carries it.
- [ ] Know which auth `claude -p` uses: on an API key the what-pass is metered spend with no cap.
- [ ] Treat backups of `<home>` as transcript backups; `<home>` itself is closed to other users (`0700`).
