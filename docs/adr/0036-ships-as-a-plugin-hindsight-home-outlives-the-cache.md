# ADR-0036: Hindsight ships as a Claude Code plugin; everything that outlives an update lives in its own home

**Date:** 2026-11-16 · **Status:** accepted · **Amends:** ADR-0001 · **Decides:** issue #69 (map #59, v2 audit core)

## Context

v1 is wired by hand. Three hook entries in the user's `settings.json`, two launchd plists and a SwiftBar wrapper all hard-code the working folder's path. Renaming that folder on 2026-11-13 meant editing all six. The v2 brief leaned towards a plugin. The MCP server is out of scope for this map (it has its own), so the case for a plugin rests on the hooks and the install alone.

A plugin brings three constraints:

- **It runs from a versioned cache.** The cache path changes on every update, and old versions are swept 14 days later.
- **It cannot install launchd jobs.** The listener and the nightly still need an install step.
- **Its own data directory is weak.** `${CLAUDE_PLUGIN_DATA}` is deleted on uninstall, and a `--plugin-dir` copy gets a different directory from a marketplace install (issue #60).

The hook behaviour below was checked against the Claude Code docs on 2026-11-16. A hook marked `"async": true` does not hold the turn, and none of its output reaches the operator. On `SessionStart`, plain stdout is added to the model's context. A JSON `systemMessage` is shown to the operator as a warning. A plugin's `bin/` is on PATH in the Bash tool only. Run on a repo-shaped root, `claude plugin validate` passes. It warns once, about the root `CLAUDE.md`, which is not loaded as plugin context.

## Decision

1. **The repo root is the plugin root**, in the house plugin layout:
   - deterministic code moves from `build/` to `cli/`;
   - `claude plugin validate` gates commits;
   - `eval/` stays as it is. It is the regression harness for the model passes, not a `claude plugin eval` suite, because the plugin has no model-invoked skill.
   - The root `CLAUDE.md` warning is expected: it is development context.
2. **The operator runs a released version**, installed from this repo as its own marketplace. Changes are tried through the house symlink route. Nothing important lives in the plugin data directory, so the split between a dev copy and a released copy costs nothing.
3. **Hindsight home** is `~/.hindsight/`, overridable by `HINDSIGHT_HOME`. It holds the database, the logs (moved from `~/Library/Logs/hindsight/`) and `current`, a symlink to the live plugin root. Every job creates its log directory at start.
4. **launchd reaches the code through `current`.**
   - A one-off install writes both plists. Each runs the interpreter the install ran under, against `~/.hindsight/current/cli/…`.
   - The labels stay `com.hindsight.ingest` and `com.hindsight.nightly`, so the install replaces v1's plists in place. It is idempotent.
   - The health check re-points `current` whenever `${CLAUDE_PLUGIN_ROOT}` differs, and restarts the listener with `launchctl kickstart -k`. An update therefore takes effect at the next session.
   - The install never edits `~/.claude/settings.json`. It prints the v1 hook entries for the operator to remove by hand, once.
5. **Two hook entries.**
   - **Capture** is one `"async": true` entry on `SessionStart`, `Stop` and `SubagentStop`. It is ADR-0033's capture hook, and it never holds a turn.
   - **The health check** is a separate synchronous `SessionStart` entry.
   - Hooks call `${CLAUDE_PLUGIN_ROOT}/cli/…` by full path.
6. **The health check:**
   - **Reads:** the health rows straight from SQLite (no HTTP), whether both launchd jobs are loaded, and whether `current` matches.
   - **When healthy:** it exits with empty output, because stdout would land in the model's context.
   - **Otherwise:** one `systemMessage` line naming the source and how long it has been stale or failing. Before install, the line is "not installed — run `/hindsight:ops install`".
   - **Never:** writes `additionalContext`, or raises an error over a missing database or job.
   - **Budget:** about 100 ms.
7. **One user-invoked skill**, `/hindsight:ops <install|uninstall|start|stop|serve|open>`, runs `${CLAUDE_PLUGIN_ROOT}/cli/hindsight.py`. It sets `disable-model-invocation`, so the model never starts or stops jobs.
   - **`install --from <path>`** moves v1's database into Hindsight home, once, after booting out the jobs. It refuses if a database is already there. The v10 migration runs on first open (ADR-0031).
   - **`uninstall`** boots out both jobs and removes the plists and `current`. It never deletes the database: compacted history cannot be rebuilt (ADR-0034). Removing `~/.hindsight/` is a manual step, which the command prints.
8. **The SwiftBar menu bar is retired.** The health check takes over showing state, and `/hindsight:ops` takes over control. That leaves four moving parts: the listener, the nightly, the hooks and the on-demand server.

## Alternatives rejected

- **Hand-wired hooks and plists, as in v1.** One folder rename touched six files.
- **The database in `${CLAUDE_PLUGIN_DATA}`.** It is deleted on uninstall and split between dev and released copies (issue #60).
- **`--plugin-dir` against the working copy as the daily driver.** It is simpler, but it is not what a release ships.
- **launchd pointing into the cache, or a launcher script.** The cache path is versioned and swept. A symlink re-pointed at session start needs no script.
- **The health check printing to stdout or `additionalContext`.** That spends the model's context on the operator's concern.
- **Keeping the menu bar.** It costs a fifth moving part and a third-party host to show health between sessions, and the audit is read in sessions anyway.
- **An `uninstall --purge`.** One flag would delete history that cannot be rebuilt.

## Consequences

- ADR-0001 is amended. Its listener and on-demand server stand. The menu-bar amendment of 2026-09-23 is withdrawn. The install step and the controls move to `/hindsight:ops`.
- `build/` → `cli/` touches every path in docs, tests and the eval runners. It is the first v2 build ticket, ahead of capture.
- **Not yet verified:** async on `Stop` and `SubagentStop`. The docs give no event whitelist, and only `SessionStart` is confirmed. The capture build ticket tests it first.
- **Health between sessions is no longer visible.** A failure surfaces at the next session start.
- CONTEXT.md gains **Hindsight home** and **Health check**, and **Menu bar plugin** is marked retired.
