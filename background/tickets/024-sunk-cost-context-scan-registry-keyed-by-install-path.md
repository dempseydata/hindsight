# #24 Sunk-cost context scan, registry keyed by install path

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

The session-start sunk-cost scan rebuilt from ccwhere's context_tree: itemise per project what every session pays before the first prompt — CLAUDE.md chain, skill descriptions, MCP schemas — into the store for the where-view's sunk-cost composition drill (plugins as a grouping level, measured-median-as-authority). The plugin registry is keyed by install path, fixing ccwhere's per-install-record scan that double-counted skills.

## Acceptance criteria

- [ ] Scan over a fixture config surface itemises CLAUDE.md chain, skills, and MCP schemas per project with sizes
- [ ] A skill reachable via two install records is counted once (keyed by install path)
- [ ] Plugins are a grouping level in the stored shape
- [ ] Results land in the store queryable per project
- [ ] Re-running the scan is idempotent

## Blocked by

- None — can start immediately (sequenced last per the red-team build order: wedge first, where-view substrate last).


---

**comment · 2026-08-17**

Shipped in 52ed450. All five acceptance criteria covered by seam tests (SunkCostTest, 11 tests): fixture-surface itemisation of CLAUDE.md chain / skills / MCP with sizes, duplicate install records counted once via the path-keyed registry, plugins as the grouping level (the plugin column), per-project querying (project rows + NULL user floor), and idempotent rescan (full replace).

The code-review pass materially reshaped the first cut, verified against this machine's real config: @-imports are now expanded (hindsight's own CLAUDE.md under-reported 12x without it — 405 vs 5,503 tokens), the plugin scan is narrowed to skills/ (ponytail's vendored .openclaw mirror doubled its count), commands are counted like skills (pm-execution ships 11), user-scope MCP reads ~/.claude.json mcpServers rather than the stale ~/.claude/mcp.json, and a corrupt settings.json degrades to an empty enablement map instead of flipping all 17 installed plugins to user scope. Known ceilings carried as ponytail comments: on-disk skill sets can exceed the loaded set (deprecated/ dirs), MCP rows are config-size proxies for wire schemas, and subdirectory sessions carry suffixed project names needing prefix-match at query time.

