# Night shift: #50 Tabler layout and card grammar — branch night-shift/tabler-look

Authority: push + tracker yes · End state: branch only · Baseline: 221 tests, 30.3 s

| Ticket | Status | Commit | Rounds | Suite | Notes |
| --- | --- | --- | --- | --- | --- |
| #51 Contract: grammar tokens, amber/caution rule, floor check | done | 440cf3a | 1 | 226 / 31.0 s | --o-stat-size 24px already live on today's tiles |
| #52 One shell for all three views | done | (see git log) | 1 | 232 / 34.4 s | browser check: chip, preset, day-set re-render; how link gains ?p= |
| #53 Stat cards with delta and trend spark | todo | | | | |
| #54 What: ledger card-table, badges, help popover | todo | | | | |
| #55 How: runs as cards, stage panels, off-script card | todo | | | | |
| #56 Where: sections as cards | todo | | | | |
| #57 Re-derive DESIGN.md, retake screenshots | human | | | | excluded: public screenshots, documenter, public push |

## Owed
- #54: style the caution and neutral badge roles (#52 styled only ok and problem)
- #53, #54, #56: JS-built markup with data-icon must call fillIcons(root) after render

## Decisions
- sitting: ten build contracts — ADR-0030 (done)
- #51: --o-radius-card in :root only (shape is theme-invariant, ADR-0017 §3) — ADR? no
- #51: block-agreement test checks every token, not only the new ones — ADR? no
- #52: brand <b>, page title <h1>, card titles <h2> — ADR? no
- #52: top bar and nav row on --o-panel — ADR? no
- #52: only ok/problem badge roles styled; caution/neutral land in #54 — ADR? no
- #52: fillIcons(root) global, for JS-built markup to call after render — ADR? no
- #52: .playwright-cli/ added to .gitignore (browser-check snapshots) — ADR? no

## Blocked

## Nits
- #51: floor-check role regex `(\w+)` skips a hyphenated role (`--o-info-x-fill`); use `(\w[\w-]*)`
- #51: floor-check asserts are bare `assert`, stripped under `python -O`; self.fail/ValueError sturdier
- #52: icons test asserts the Object.hasOwn source text, not behaviour (no JS runtime)
- #52: card header with subtitle renders 68px (#42 says >=65px)
- #51: DESIGN.md still says 28px stat numerals — re-derived in #57
