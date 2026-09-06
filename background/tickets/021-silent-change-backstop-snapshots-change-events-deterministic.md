# #21 Silent-change backstop: snapshots, change events, deterministic linking

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

Analysis runs capture the config surface (the listener stays ingest-only): project `.claude` git history (commits only), snapshots of the ~/.claude text-config surface, and structural `installed_plugins.json` diffs. Content lands as content-addressed `blobs` (sha256) with one `change_events` table; diffs are computed at render time, not stored. First run is a silent baseline. Change events link to why-findings by deterministic name+window matching — no model in the loop; an unlinked change reads "changed, no stated rationale". Noise policy is render-time and out of scope.

## Acceptance criteria

- [ ] First run over a fixture config surface produces blobs and a baseline, no change events
- [ ] A config edit between runs produces one change event with before/after blob hashes
- [ ] Identical content stored once (content-addressed)
- [ ] A change whose name matches a same-window finding gets linked; one without stays unlinked
- [ ] A structural plugins diff (install/update) is detected as its own source type
- [ ] Second run with no changes produces no new events (idempotent)

## Blocked by

- #18


---

**comment · 2026-08-17**

Landed in 84499c8. All six acceptance criteria implemented and tested through the analysis-run entrypoint (8 new seam tests; full suite 42/42 green).

Two implementation decisions worth knowing, both marked in code:

1. **The ~/.claude text-config surface is a fixed five-file list** (CLAUDE.md, settings.json, settings.local.json, keybindings.json, mcp.json). agents/, hooks/, commands/ are not captured — widen `BACKSTOP_SURFACE` if a silent change ever lands outside the list.
2. **Snapshot/plugins events are dated at capture time** (the change's true time between runs is unknowable), so the 7-day linking window is sensitive to run cadence: infrequent runs can push a change's finding out of window. The miss reads "no stated rationale", never a wrong link. Git-sourced events use real commit dates and don't have this problem.

Also: per-plugin structural events carry whole-file before/after blob hashes, so the render-time differ should re-run the structural extraction rather than naively diffing the blob pair; and rewritten project git history rebaselines silently (ponytail-marked).

