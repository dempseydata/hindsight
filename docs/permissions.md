# Permissions

## Principals

| Principal | What it is | Credential |
| --- | --- | --- |
| Operator | The macOS user running the tool | Filesystem ownership of the repo and `local-data/`; ability to reach loopback |
| Local process | Anything else running as any user on this Mac | Ability to open `127.0.0.1:4318` or `:8321` |
| Model (`claude -p`) | Subprocess started by the analysis run | None — its output is data, gated before write |

There are no roles, claims, tokens, cookies or logins. Scope is not derived from anything: every
request to either server is served as the operator. This is a deliberate consequence of ADR-0001
(loopback, on-demand foreground) and is the whole access-control model.

## Resource × operation matrix

| Resource | Read | Write | Enforced by |
| --- | --- | --- | --- |
| `otel_events`, `otel_metrics` | Serve (`/where`) | Listener (any local POST) | Loopback bind; SQLite `mode=ro` on the serve side |
| `sessions`, `audit`, `tool_events`, `usage`, `command_grains`, `status_narrative`, `sunk_cost`, `project_presence`, `excluded_sessions` | Serve | Analysis run, backfill importer | Code: only `analyze.py`/`substrate.py`/`sunk_cost.py`/`import_backfill.py` open the DB writable |
| `blobs`, `change_events`, `backstop_state` | Nothing serves them | Analysis run | Not exposed on any route; readable only by opening the DB file |
| `~/.claude/projects/**/*.jsonl` transcripts | Analysis run | Never | Code reads only; no delete path exists |
| `~/.claude/{CLAUDE.md, settings*.json, keybindings.json, mcp.json}`, `plugins/installed_plugins.json` | Analysis run (copied verbatim into `blobs`) | Never | — |
| Workspace repos `~/Documents/Claude/*` | Analysis run (`git` history of `.claude/`, `CLAUDE.md` chain, skills, MCP config, `.claude/my-process.md`); Serve (`.claude/my-process.md` of the `?p=` project) | Never | `?p=` membership-checked against DB project names (`serve.py:496`) |
| `local-data/analysis/` extracts and model cache | Analysis run | Analysis run (write, unlink on invalidation) | Filesystem |
| `~/Library/LaunchAgents/com.hindsight.*.plist` | launchd | `listener.py install/uninstall`, `analyze.py install/uninstall` | Filesystem; `launchctl` as the user |
| `design/tokens.css`, `build/assets/*` | Serve, per request | Never at runtime | Literal filenames only |

## Row-level security

None. SQLite has no RLS; every check above is either a network bind, a SQLite open mode, or which
module holds the connection. There is no per-row ownership because there is one owner.

## Where a check is missing, and whether it matters

| Gap | Fact | Consequence |
| --- | --- | --- |
| Listener accepts any local writer | No auth, no size cap, unknown paths `200` (`listener.py:143-173`) | Any local process can pollute `otel_events`. On a single-user Mac the writer set is the operator's own processes. |
| Serve has no auth | `serve.py:596` | Any local process can read the rendered views — session titles, model prose, project names, consumer names. Not the `blobs` table. |
| `blobs` holds config verbatim | `analyze.py:864-868, 816-817` | Reading the DB file reveals every settings/MCP file, current and historical. Protected only by the file's Unix mode and the gitignore. See [variables.md](variables.md). |
| Model output gated by shape, not content | `valid_entry` (`analyze.py:598`), `contract` (`score.py:119`) | A well-formed but wrong entry is written. The eval set (`eval/`) is the standing check on that; see [automation.md](automation.md). |
