# Plugin data directory: a persistent location outside the versioned cache

Research for [#60](https://github.com/dempseydata/hindsight/issues/60), part of map [#59](https://github.com/dempseydata/hindsight/issues/59). Checked 2026-11-13 against Claude Code 2.1.312.

**Key:** **[V]** verified: stated in official docs or observed on disk. **[I]** inferred: reasoned from verified facts, not stated anywhere.

## Answer

Yes. Claude Code gives every plugin `${CLAUDE_PLUGIN_DATA}` = `~/.claude/plugins/data/<id>/`, outside the versioned cache, kept across updates. Hooks and a stdio MCP server get it both as an inline substitution and as an exported env var. A launchd job gets nothing from Claude Code, so its plist has to hard-code the resolved path. That works, with three caveats:

1. **The path depends on how the plugin was loaded.** `hindsight@<marketplace>` and the `--plugin-dir` dev copy (`hindsight@inline`) get different directories.
2. **Uninstalling deletes the directory** unless `--keep-data` is passed.
3. **Code a launchd job runs must not live under `${CLAUDE_PLUGIN_ROOT}`.** That path is versioned, and old version directories are swept 14 days after an update.

**Recommendation [I]:** keep the SQLite database and the launchd entry point at a fixed path the product owns, `~/.hindsight/`, outside `~/.claude/plugins/` entirely. Use `${CLAUDE_PLUGIN_DATA}` only for regenerable things such as caches and dependency installs. See [Recommendation](#recommendation).

## Findings

### 1. The directory exists, and where it lives [V]

- `${CLAUDE_PLUGIN_DATA}` resolves to `~/.claude/plugins/data/<id>/`. It is "created on first reference and kept across plugin updates". `<id>` is the plugin identifier with every character other than a letter, digit, `_` or `-` replaced by `-`. Source: <https://code.claude.com/docs/en/plugins-reference#environment-variables>
- The plugin identifier has the form `<name>@<origin>`. The origin is a marketplace name, `inline` (`--plugin-dir`, `--plugin-url`, `CLAUDE_CODE_PLUGIN_DIRS`), `skills-dir`, or `synced`. Source: <https://code.claude.com/docs/en/plugins/loading#find-where-a-plugin-came-from>
- On this machine, `~/.claude/plugins/data/` holds `playwright-claude-plugins-official`, `playwright-inline`, `pdf-viewer-inline`, `pdf-viewer-synced`, `ponytail-ponytail` and others. The same plugin gets a separate directory for each origin. Source: local `ls ~/.claude/plugins/data/`. The ids in `~/.claude/plugins/installed_plugins.json` have the form `playwright@claude-plugins-official`.
- The plugins root is `~/.claude/plugins` unless `CLAUDE_CODE_PLUGIN_CACHE_DIR` is set. If it is set, the data directory moves with it. Source: <https://code.claude.com/docs/en/plugins/loading#find-plugins-on-disk>

### 2. It survives updates; `${CLAUDE_PLUGIN_ROOT}` does not [V]

- `${CLAUDE_PLUGIN_ROOT}` points at `cache/<marketplace>/<plugin>/<version>/`. "A plugin's root path changes with every version. Keep a plugin's durable files in `${CLAUDE_PLUGIN_DATA}` instead." Source: <https://code.claude.com/docs/en/plugins/loading#find-plugins-on-disk>
- On an update or an uninstall, the previous version directory gets an `.orphaned_at` marker and is removed by a background cleanup 14 days later. Source: <https://code.claude.com/docs/en/plugins/loading#cleanup-of-previous-versions>
- If a plugin updates mid-session, hooks, MCP and LSP servers keep the old version's path until `/reload-plugins` runs. Source: <https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs>

### 3. It does not survive uninstall by default [V]

- "By default, Claude Code deletes the `${CLAUDE_PLUGIN_DATA}` directory when you uninstall the plugin from the last place it's installed." `claude plugin uninstall --keep-data` preserves it. The directory also stays when another installed plugin maps to the same folder, or when the install records can't be read back after the uninstall. Sources: <https://code.claude.com/docs/en/plugins-reference#environment-variables>, <https://code.claude.com/docs/en/plugins/cli-reference#plugin-uninstall>

### 4. Which components can reach it [V]

The table below is from <https://code.claude.com/docs/en/plugins-reference#where-each-variable-resolves>.

| Component | `${...}` substituted in | Exported to the process |
| --- | --- | --- |
| Hook commands | `command`, `args` | `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_OPTION_*` |
| MCP `stdio` server | `command`, `args`, `env` | `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR` |
| Monitors | `command` | none |
| Skill, command and agent Markdown | body | not applicable |
| Bash tool, main session or subagent | none | none: "The variables aren't present in the environment of commands Claude runs through the Bash tool" |
| launchd job | n/a: not a Claude Code component | none |

Real use in the installed plugin cache:

- `claude-security` hooks read `$CLAUDE_PLUGIN_DATA` from the environment. Source: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/claude-security/hooks/hooks.sh`, lines 26–27
- `code-modernization` reads it and falls back to `$TMPDIR` when it is unset. Source: `.../plugins/code-modernization/scripts/telemetry.sh`, line 58
- Anthropic's `plugin-dev` guide gives the pattern a SQLite MCP server would use, `"args": [..., "--db-path", "${CLAUDE_PLUGIN_DATA}/data.db"]`, and notes that the directory is "one folder per plugin, shared by all projects". Source: `.../plugins/plugin-dev/skills/mcp-integration/references/server-types.md`, lines 465–483

### 5. launchd [I]

- launchd starts `ProgramArguments` without a shell (see `man launchd.plist`), so a plist can't read `$CLAUDE_PLUGIN_DATA` or expand `~`. Whatever writes the plist has to write absolute paths into it. The man page doesn't mention tilde expansion; the conclusion that it doesn't happen is inferred.
- A plist that points at a script under `${CLAUDE_PLUGIN_ROOT}` keeps working after an update only until the 14-day sweep removes that version directory. After that it fails silently at its next scheduled run. This follows from finding 2.
- A plist that points into `${CLAUDE_PLUGIN_DATA}` outlives updates. It still breaks if the plugin is uninstalled or loaded under a different origin (dev `inline` versus a marketplace install), and if `CLAUDE_CODE_PLUGIN_CACHE_DIR` changes.

## Recommendation

All of this section is inferred **[I]**.

For hindsight, the database is the audit history and can't be regenerated (#59: "~150 sessions now exist only as derived rows"). The default delete on uninstall, and the per-origin split between the dev and installed copies, both put that history at risk. The recommendation:

1. **The database goes at a fixed, product-owned path,** such as `~/.hindsight/hindsight.db`, overridable by one environment variable. `~/Library/Application Support/hindsight/` is the macOS-native alternative. Hooks and the MCP server get the path from that variable or the default, never from `${CLAUDE_PLUGIN_DATA}`. One database is then shared by the dev copy, the installed copy and launchd, and no plugin lifecycle event can delete it.
2. **The launchd job gets a stable entry point in that same directory,** a small launcher at `~/.hindsight/bin/`. A SessionStart hook (or the install step) refreshes it from `${CLAUDE_PLUGIN_ROOT}` whenever the version changes. The plist is written once with absolute paths to the launcher and the database, and never points into `cache/`.
3. **`${CLAUDE_PLUGIN_DATA}` is still the right place for anything that can be rebuilt,** such as a dependency install, a cache or a lock file. It is managed for the plugin, and losing it costs nothing.

If the product prefers to stay inside Claude Code's conventions, the alternative is the database in `${CLAUDE_PLUGIN_DATA}`, with the uninstall loss documented and `--keep-data` named in the README. That alternative still needs the launchd launcher copied out of `${CLAUDE_PLUGIN_ROOT}`, and it still splits the database between the dev and installed origins.

## Not checked

- Whether `${CLAUDE_PLUGIN_DATA}` is set for hooks of a plugin loaded from `@skills-dir`. The docs don't single out any origin, but this wasn't tested.
- The actual behaviour of uninstall and `--keep-data` was not run here. The documented behaviour is taken as given.
