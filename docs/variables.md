# Variables, paths and secrets

Hindsight reads **one** environment variable (`PATH`, at install time, to bake into the nightly
plist) and no config file of its own. Everything else is a hard-coded path or a CLI flag. The
secret surface is therefore not "which env vars leak" but "which files get copied into the DB".

## Configuration

| Name | Used by | Source | Default | Override | Risk |
| --- | --- | --- | --- | --- | --- |
| Listener port | `listener.py:27`, `hook.py:39` | constant | `4318` | `--port` on both (the launchd plist passes none, so the daemon always uses the default) | Low — port mismatch means silent hook loss |
| Serve port | `serve.py:72` | constant | `8321` | `--port` | Low |
| DB path | `listener.py:26`, `analyze.py:80`, `serve.py` | `REPO/local-data/hindsight.db` | — | `--db` | **Holds secrets** (below) |
| Transcript root | `analyze.py:79` | `~/.claude/projects` | — | `--root` | Personal data source |
| Claude dir | `analyze.py:115`, `sunk_cost.py` | `~/.claude` | — | `--claude-dir` | Config with possible tokens |
| Workspace dir | `analyze.py:84` | `~/Documents/Claude` | — | `--projects-dir` | Git history of every project's `.claude/` |
| Work dir | `analyze.py` | `REPO/local-data/analysis` | — | `--work-dir` | Plain-text extracts |
| Model id | `analyze.py:129` | constant `claude-haiku-4-5-20251001` | — | none | Pinned on purpose (ADR-0002); recorded on every `audit` row |
| Prompt versions | `analyze.py:126, 130-133` | constants `what-v3`, `merge-v1`, `status-v1` | — | none | Recorded on every row; changing one invalidates the cache directory name |
| Call timeout | `analyze.py:149` | `300` s | — | none | — |
| Hook timeout | `hook.py:43` | `0.5` s per leg; `5` s harness-side in `~/.claude/settings.json` | — | none | — |
| Nightly hour | `analyze.py:973` | `3` | — | none | — |
| `PATH` | `analyze.py:984` | installing shell's `PATH`, written to the nightly plist | — | re-run `install` | `claude` must be on it (ticket #84) |

## Outside the repo

| File | Content | Owner |
| --- | --- | --- |
| `~/.claude/settings.json` | `OTEL_*` exporter env pointing Claude Code at `:4318`; three hook entries invoking `build/hook.py` by absolute path | Operator, edited by hand |
| `~/Library/LaunchAgents/com.hindsight.ingest.plist` | Absolute `sys.executable` + `listener.py`; `KeepAlive`; log to `~/Library/Logs/hindsight/listener.log` | Written by `listener.py install` |
| `~/Library/LaunchAgents/com.hindsight.nightly.plist` | Absolute `sys.executable` + `analyze.py`; `StartCalendarInterval 03:00`; `PATH`; log to `~/Library/Logs/hindsight/analyze.log` | Written by `analyze.py install` |

Both plists pin the Python binary and repo path at install time. Moving the repo or upgrading
Homebrew Python requires `uninstall` + `install` on each.

## Secrets

Hindsight has no secrets of its own — no API key (the model runs through the `claude` CLI's own
login), no tokens, no signing keys. What it has is **other people's secrets copied in**:

| Where | What | How it gets there | Exposure |
| --- | --- | --- | --- |
| `blobs.content` | Full text of `~/.claude/settings.json`, `settings.local.json`, `mcp.json`, `keybindings.json`, `CLAUDE.md`, `plugins/installed_plugins.json` — current and every changed version since first run | `capture_backstop`, `analyze.py:864-868` | Anyone who can read `hindsight.db`. **Not** served by any route. |
| `blobs.content` | Every historical version of every `.claude/*` file in every workspace repo, including `settings.local.json` and `.mcp.json` if they were ever committed | `_capture_project_git`, `analyze.py:816-817` | Same |
| `local-data/analysis/extracts/` | User and assistant message text, 1,500 chars per piece — whatever the operator pasted into a session | `extract.py` | Filesystem |
| `local-data/analysis/what-v3/` | Raw model output | `analyze.py:623-624` | Filesystem |
| `~/Library/Logs/hindsight/analyze.log` | First 80 chars of any rejected model output | `analyze.py:621` | Filesystem |
| `tool_events.file_path`, `sunk_cost.path`, `sessions.transcript_path` | Absolute paths on this machine | substrate, sunk-cost, sync | Served on `/where` and `/how` |

**Client-side bundling:** nothing. The views embed query results as JSON in the page; no key,
token or config value exists to bundle. `blobs` is never queried by `serve.py`.

## Rotation

If `hindsight.db` or `local-data/` is ever copied off the machine or committed: treat every key in
`~/.claude/settings*.json`, `~/.claude/mcp.json` and any workspace `.claude/settings.local.json` /
`.mcp.json` as exposed and rotate them. Deleting rows from `blobs` does not remove them from a
copy already taken.

## Pre-go-live checklist

This tool is not deployed; "go-live" is a repo going public (the `hindsight-app` export). Before that:

- [ ] `local-data/` absent from the export and from every historical commit (it is gitignored here; the export has fresh history).
- [ ] No screenshot under `docs/screenshots/` shows a real transcript path, project name or model prose the operator would not publish.
- [ ] `~/.claude/settings.json` hook entries and OTEL env documented for the reader as *their* config to add, not shipped.
- [ ] `eval/` present in the export — it is a runtime import (`analyze.py:147`, `serve.py:65`), not just tests.
