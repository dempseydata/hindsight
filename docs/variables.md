# Variables, paths and secrets

Hindsight reads **two** environment variables (`HINDSIGHT_TZ`, `PATH`) and no config file of its own.
Everything else is a hard-coded constant or a CLI flag. The secret surface is not "which env vars
leak" but "which files get copied into the DB" — and, since a push to this repo is a deploy, "what
must never be committed".

## Configuration

Scope: **server** = the Python processes (listener, nightly analysis, serve); **client** = the browser.
Rotation "re-install" means `uninstall` + `install` on the plist that bakes the value.

| Name | Used by | Scope | Source | Rotation | Risk |
| --- | --- | --- | --- | --- | --- |
| `HINDSIGHT_TZ` | `analyze.apply_tz` at import — so serve, how, import_backfill too | server | env, IANA name; unset = host zone; baked into the nightly plist at install | re-install | Low — moves every day bucket; a bad name is one stderr line and the host zone |
| `PATH` | `analyze.nightly_plist` | server | installing shell's `PATH`, baked into the nightly plist | re-install | `claude` must resolve on it or the nightly run is silent |
| Listener port | `listener.py` `DEFAULT_PORT`, `hook.py --port` | server | constant `4318`; `--port` on both (the plist passes none) | — | Low — mismatch is silent hook loss |
| Serve port | `serve.py` `DEFAULT_PORT`, `--port` | server | constant `8321`; binds `127.0.0.1` only | — | Low |
| DB path | listener, analyze, serve, how, import_backfill — `--db` | server | `REPO/local-data/hindsight.db` | — | **Holds copied-in secrets** (below) |
| Transcript root | `analyze.py --root` | server | `~/.claude/projects` | — | Personal data source |
| Claude dir | `analyze.py --claude-dir` | server | `~/.claude`; reads `BACKSTOP_SURFACE` (`CLAUDE.md`, `settings.json`, `settings.local.json`, `keybindings.json`, `mcp.json`) + `plugins/installed_plugins.json` | — | Config with possible tokens |
| Projects dir | `analyze.py`, `serve.py`, `attribute` — `--projects-dir` | server | `~/Documents/Claude`; every child with `.git` is captured, `.claude/my-process.md` read by the how-view | — | Git history of every project's `.claude/` |
| Work dir | `analyze.py --work-dir` | server | `REPO/local-data/analysis` (`extracts/`, `what-v3/`) | — | Plain-text extracts and raw model output |
| Backfill dir | `import_backfill.py --backfill-dir` | server | `REPO/local-data/backfill` | — | Same |
| Model pin | `analyze.MODEL` (what, merge, status passes; stamped on every `audit`/narrative row); `eval/cases.json` and `eval/what_cases.json` `"model"` | server | constant `claude-haiku-4-5-20251001` in **three places** | change all three together, run `eval/` first | Drift between the copies makes the eval gate measure a different model than production |
| Prompt versions | `analyze.PROMPT_VERSION` `what-v3`, `merge-v1`, `STATUS_VERSION` `status-v1` | server | constants → `build/prompts/<v>.txt` | — | Recorded on every row; the what cache dir is keyed by version |
| Schema version | `analyze.init_db` `PRAGMA user_version` | server | `9` (v9 = `tool_events.error_text`, ADR-0027; v8 and v9 wipe and rescan every surviving transcript) | — | A downgrade is not supported |
| `claude -p` timeout | `analyze.CALL_TIMEOUT`; `eval/run.py` literal | server | `300` s | — | — |
| Subprocess timeouts | `git`, `claude --version` | server | `30` s | — | — |
| SQLite | all connections `timeout=30`; WAL; listener `busy_timeout=5000` | server | constants | — | — |
| Hook budget | `hook.py TIMEOUT` | server | `0.5` s per blocking leg (stdin, connect, response) | — | Never stalls a session; the harness-side timeout is Claude Code's own |
| Nightly hour | `analyze.NIGHTLY_HOUR` | server | `3` (03:00, `StartCalendarInterval`) | — | — |
| Tuning constants | `serve.CHIP_SHARE` `0.01`; `extract.PER_MSG_CAP` `1500`, `CHUNK_CAP` `180000`; eval pools 4 / 6 threads | server | constants | — | Display and extraction only |
| `?p=` | `serve.py` how-view, `chrome.js` chips | client → server | URL query; an unknown project falls back to the busiest declaring one | — | Project names only |
| `theme` | `theme.js` | client | `localStorage`; `light` / `dark`, absent = system (ADR-0017) | toggle back to system removes it | None — one word, per browser |
| `filter` | `chrome.js`, `how.js` | client | `sessionStorage`, per tab: window preset, active chips, hide-cache-reads; dies with the tab | — | Project names only |

## Outside the repo

| File | Content | Owner |
| --- | --- | --- |
| `~/.claude/settings.json` | Claude Code's OTEL exporter env pointing at `:4318`; hook entries (`SessionStart`, `UserPromptSubmit`, `Stop`) invoking `build/hook.py` by absolute path | Operator, by hand |
| `~/Library/LaunchAgents/com.hindsight.ingest.plist` | Absolute `sys.executable` + `listener.py`; `KeepAlive`; no env | `listener.py install` |
| `~/Library/LaunchAgents/com.hindsight.nightly.plist` | Absolute `sys.executable` + `analyze.py`; 03:00; `PATH` and, if set, `HINDSIGHT_TZ` | `analyze.py install` |
| `~/Library/Logs/hindsight/{listener,analyze}.log` | Process logs; `analyze.log` carries the first 80 chars of any rejected model output | launchd |

Both plists pin the Python binary and repo path at install time; moving the repo or upgrading Python
means re-install. The hook sends the workspace folder's **inode**, never its path (ADR-0018).

## Secrets

Hindsight has none of its own — no API key (the model runs through the `claude` CLI's login), no
tokens, no signing keys. What it has is **other people's secrets copied in**:

| Where | What | How | Exposure |
| --- | --- | --- | --- |
| `blobs.content` | Full text of the backstop surface and `installed_plugins.json`, current and every changed version since first run | `capture_backstop` | Anyone who can read `hindsight.db`. **Never queried by `serve.py`.** |
| `blobs.content` | Every committed version of every `.claude/*` file in every workspace repo — `settings.local.json`, `.mcp.json` included if ever committed | `_capture_project_git` | Same |
| `tool_events.error_text` | Verbatim text of every failed tool result (ADR-0027): stderr, tracebacks, absolute paths, whatever a command printed | `substrate.py` | **Served** in the where blob (`errs[].t`) |
| `local-data/analysis/extracts/`, `what-v3/` | Message text (1,500 chars per piece) and raw model output | `extract.py`, `analyze.py` | Filesystem |
| `local-data/eval/` | what-pass extracts (the regression set's real inputs), run outputs, the Stage B dry-run material (`so-what/`) | `eval/*.py` | Filesystem, untracked |

**Rotation:** if `hindsight.db` or `local-data/` is ever copied off the machine or committed, treat
every key in `~/.claude/settings*.json`, `~/.claude/mcp.json` and any workspace `.claude/settings.local.json`
/ `.mcp.json` as exposed and rotate. Deleting `blobs` rows does not recall a copy already taken.

**Client-side bundling:** each page inlines `tokens.css`, the view's JS, and JSON blobs as `const`s:
`DATA` (per-day token totals by project, chip names, hidden list, sync date), `WHAT` (audit rows:
session id, project, day, skip/ADR flags, and the model-written title and sections — prose derived
from transcripts), `WHERE` (tool, lens, session, subagent, model, latency, hook, retry, MCP-connection
rows; `errs` with the verbatim error text above; sunk-cost plugin and skill names with tokens; medians;
coverage). The how-view is server-rendered HTML with no blob. No key, token or path constant exists to
bundle; no absolute path is served — `error_text` is the one served field that can carry one.

## Pre-go-live checklist

This repo is born public: every push is go-live. Before one:

- [ ] `git config core.hooksPath .githooks` is set in this clone — the pre-commit hook is opt-in per clone and refuses staged additions matching `.githooks/denylist.txt` (`/Users/<name>`, `sk-ant-`, `ghp_`, `AKIA`, private-key headers, `<uuid>.jsonl`). Extend the list; never bypass it.
- [ ] `local-data/` is gitignored and absent from history; `hindsight.db` and its `.bak-*` copies never staged.
- [ ] `docs/screenshots/*.png` (the one un-ignored png path) were taken from a filtered or synthetic view — the where-view's error rows and the what-view's audit prose are transcript-derived.
- [ ] `eval/cases.json` ledgers are committed in full by design (reviewed, ticket 087); `eval/what_cases.json` carries expectations only — its extracts stay under `local-data/eval/what/extracts/`. No so-what dry-run script exists under `eval/`; its material is untracked.
- [ ] Issue bodies and `background/` cite sessions by id, never by transcript text or home path.
- [ ] `security-preflight` run before any push touching `eval/`, `docs/screenshots/` or `background/`.
- [ ] `~/.claude/settings.json` hook entries and OTEL env are documented as the reader's config to add, never shipped.
