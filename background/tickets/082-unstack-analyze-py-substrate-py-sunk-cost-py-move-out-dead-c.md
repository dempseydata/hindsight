# #82 Unstack analyze.py: substrate.py + sunk_cost.py move out; dead config cluster deleted (review C3)

state: closed · labels: ready-for-agent · opened: 2026-08-30 · closed: 2026-08-30

> *Settled by grilling on 2026-08-30 (architecture review, candidate C3). Implement in a fresh session, after #81 (no hard dependency — just avoids rebase noise in analyze.py).*

## Summary

`build/analyze.py` (1505 lines) is stacked, not tangled: fourteen coherent clusters in one file. Two of them have zero coupling to the model pipeline and pass the deletion test with real leverage — the **substrate scan** (:488–703, the transcript JSONL grammar, streamed-response dedup, `_cli_program`/`_cli_kind` consumer classification) and the **sunk-cost scan** (:1127–1365, 12 helpers, the plugin-registry-by-install-path dedupe, `@`-import chain expansion, `.claude.json` scope resolution). Lift them into their own modules with their existing signatures as the interface. Pure relocation — no behaviour change.

## Decisions (all settled — do not re-litigate)

1. **Two modules move, not three**: `build/substrate.py` (`scan_transcript(path)` pure + `fill_substrate(conn)` + helpers) and `build/sunk_cost.py` (`scan_sunk_cost(conn, claude_dir, projects_dir)` + helpers). The **backstop stays** in analyze.py: self-contained but zero leverage (renders nowhere, ADR-0006) — it can follow the day its capture ever renders.
2. **`plugin_entries` moves to `sunk_cost.py`** (the registry parse is its concept); the backstop code in analyze.py imports it. Import direction analyze→sunk_cost only.
3. **`adr_count` moves to `substrate.py`** — derived purely from `tool_events`; `insert_results` imports it. `substrate.py` is a leaf (imports only `extract` for `FILE_TOOLS`); it must never import `analyze` — the alternative direction is a cycle-in-waiting.
4. **Tests split with a shared helpers module**: `build/test_helpers.py` gets `DbHelpers`, the transcript-builder stack (`write_transcript`, `write_records`, `rec`, `big_turns`, `_backdate`) and the TZ pin; `SubstrateTest` → `build/test_substrate.py`, `SunkCostTest` → `build/test_sunk_cost.py`; `test_analyze.py` imports the helpers too and drops ~500 lines.
5. **The dead config cluster rides along**: delete `DEFAULT_CONFIG` (analyze.py:168), `load_config` (:286) and `ConfigTest` (test_analyze.py:1615) — zero production callers, three tests testing an unused module (review C7, Strong).
6. **Import convention**: bare sibling imports, as `build/` already does (`from extract import FILE_TOOLS`). The wider eval↔build mutual `sys.path` hack is out of scope.
7. **Docs: nothing** — "Substrate scan" and "Sunk cost" are already CONTEXT.md vocabulary; the module names now match it. No new ADR.

## Acceptance criteria

- [ ] `build/substrate.py` and `build/sunk_cost.py` exist with the interfaces above; `analyze.py` ≈ 900 lines; `run_analysis`'s ordering unchanged.
- [ ] `substrate.py` imports nothing from `analyze`; `sunk_cost.py` imports nothing from `analyze`.
- [ ] `load_config` / `DEFAULT_CONFIG` / `ConfigTest` are gone.
- [ ] Full test suite green (`test_substrate.py`, `test_sunk_cost.py`, `test_helpers.py` in place; `test_analyze.py` shrunk).
- [ ] Smoke: a real `python3 build/analyze.py` run exits 0 with zero session-status changes.

## Out of scope

- Moving the backstop cluster (revisit when its capture renders somewhere).
- The extract-cache store (review C4), model-transport changes (C5), launchd twin merge (C7).
- Packaging `build/`/`eval/` properly or removing the mutual path hacks.



---

**comment · 2026-08-30**

Done in a89b67a.

- build/substrate.py (245 ln) and build/sunk_cost.py (267 ln) exist with the settled interfaces; both are leaves (substrate imports only extract; sunk_cost stdlib only) — verified by grep, no analyze import in either. One addition beyond the ticket text: `_is_live`/`LIVE_WINDOW_S` moved into substrate.py because `fill_substrate` depends on them — keeping them in analyze would have forced the forbidden substrate→analyze direction. analyze imports them back.
- `plugin_entries` + `PLUGINS_FILE` live in sunk_cost.py; the backstop imports both (analyze→sunk_cost only).
- `adr_count` in substrate.py; `insert_results` imports it.
- `load_config` / `DEFAULT_CONFIG` / `DEFAULT_CONFIG_PATH` / `ConfigTest` gone. The nightly-plist test that rode inside ConfigTest was not a config test — it survives as `NightlyTest` in test_analyze.py.
- Tests split: test_helpers.py (DbHelpers, transcript builders, StubRunner, fixture constants, TZ pin), test_substrate.py (58 incl. sunk-cost file: SubstrateTest 43 + SunkCostTest 15), test_analyze.py shrunk 1729→805 lines; test_import_backfill repointed at test_helpers. Full suite: 145 tests, green. Code review confirmed every relocated function AST-identical to its original (only content change: `analyze.LIVE_WINDOW_S`→`LIVE_WINDOW_S` in `_backdate`).
- analyze.py: 1523→1018 lines (ticket estimated ≈900; the delta is the ticket's arithmetic, nothing extra was kept). `run_analysis` ordering unchanged.
- Smoke: real `python3 build/analyze.py` exited 0. Status diff was not literally zero: four real sessions created since the last nightly ran forward to `done` (incl. the standing pending deb00ce8), and the implementing session itself synced as `pending` (live, guard-skipped). No existing session regressed — the criterion's intent (no refactor-induced status churn) holds.

