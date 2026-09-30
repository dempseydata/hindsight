# Night shift: #50 Tabler layout and card grammar — branch night-shift/tabler-look

Authority: push + tracker yes · End state: branch only · Baseline: 221 tests, 30.3 s

| Ticket | Status | Commit | Rounds | Suite | Notes |
| --- | --- | --- | --- | --- | --- |
| #51 Contract: grammar tokens, amber/caution rule, floor check | done | 440cf3a | 1 | 226 / 31.0 s | --o-stat-size 24px already live on today's tiles |
| #52 One shell for all three views | done | bb2abf5 | 1 | 232 / 34.4 s | browser check: chip, preset, day-set re-render; how link gains ?p= |
| #53 Stat cards with delta and trend spark | done | 01b9f6a | 1 | 233 / 30.7 s | browser check: day-set 09-23,24,26 → one segment + dot, delta —; preset 14 hues per card |
| #54 What: ledger card-table, badges, help popover | done | 3316edc | 0 | 236 / 33.6 s | browser check: card-table + group rows, anchors, popover by mouse/keyboard both themes |
| #55 How: runs as cards, stage panels, off-script card | done | (next row's commit) | 1 | 238 / 36.4 s | browser: runs 8px cards + stage rule, stage panels 6px, now badge on ok pair, no hue on text |
| #56 Where: sections as cards | todo | | | | |
| #57 Re-derive DESIGN.md, retake screenshots | human | | | | excluded: public screenshots, documenter, public push |

## Owed
- #56: reuse the help helper _help(pid, note) and .o-help/.o-pop; coverage-gap sentences stay visible (ADR-0030 §4)
- #56: JS-built markup with data-icon must call fillIcons(root) after render

## Decisions
- sitting: ten build contracts — ADR-0030 (done)
- #51: --o-radius-card in :root only (shape is theme-invariant, ADR-0017 §3) — ADR? no
- #51: block-agreement test checks every token, not only the new ones — ADR? no
- #52: brand <b>, page title <h1>, card titles <h2> — ADR? no
- #52: top bar and nav row on --o-panel — ADR? no
- #52: only ok/problem badge roles styled; caution/neutral land in #54 — ADR? no
- #52: fillIcons(root) global, for JS-built markup to call after render — ADR? no
- #53: first synced day = heatmap start on what, DATA.range[0] on where — ADR? no
- #53: trend spark spaces selected days by position (ordinal axis; run breaks mark gaps), settled by ADR-0029 §6 — ADR? no
- #53: delta carries a sign (+12%) — ADR? no
- #53: undated rows count in the current window, never the prior — ADR? no
- #53: o-stat-grid / o-stat-head, 4 columns (2 below 720px); pressed bar on --o-accent — ADR? no
- #54: ledger card untitled; header row project / session / entry — ADR? no
- #54: card-table header tint var(--o-bg); .o-card-table-group / .o-card-table-row — ADR? no
- #54: ledger rows lose the old border-colour hover — ADR? no
- #54: popover anchored by CSS position-area, centred where unsupported; shared helper _help(pid, note) — ADR? no
- #55: Status's 3px rule takes the current run's stage hue (off hue when the current run is off-script); dashed when there are no runs — ADR? no
- #55: section-title h2s keep the small uppercase label style, glyph beside them — ADR? no
- #52: .playwright-cli/ added to .gitignore (browser-check snapshots) — ADR? no

## Blocked

## Nits
- #51: floor-check role regex `(\w+)` skips a hyphenated role (`--o-info-x-fill`); use `(\w[\w-]*)`
- #51: floor-check asserts are bare `assert`, stripped under `python -O`; self.fail/ValueError sturdier
- #55: only the off-hue Status rule is tested
- #55: .o-stage-panel restates .panel's rules (chrome.css:143-145); collapse once where drops .panel
- #55: QuietHowTest conn.close() not in finally; borrows ServerTest.get — a module-level get(port, path) is cleaner
- #54: what.css:19 project badge sits ~2px low — add vertical-align: top
- #54: "entry" header labels the counts column; empty <span></span> third cells can go
- #54: light-theme header tint (--o-bg) reads lighter than the rows
- #53: __proto__ day key throws in dayCounts / pollutes where's at() (existing code; unreachable — keys are SQL dates)
- #53: priorWin gives NaN with tFrom set and no tTo (unreachable)
- #52, #53: tests assert literal source strings — brittle to harmless refactors (no JS runtime in the suite)
- #52: icons test asserts the Object.hasOwn source text, not behaviour (no JS runtime)
- #52: card header with subtitle renders 68px (#42 says >=65px)
- #51: DESIGN.md still says 28px stat numerals — re-derived in #57
