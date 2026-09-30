# Night shift: #50 Tabler layout and card grammar — branch night-shift/tabler-look

Authority: push + tracker yes · End state: branch only · Baseline: 221 tests, 30.3 s

| Ticket | Status | Commit | Rounds | Suite | Notes |
| --- | --- | --- | --- | --- | --- |
| #51 Contract: grammar tokens, amber/caution rule, floor check | done | 6ba8682 | 1 | 226 / 31.0 s | --o-stat-size 24px already live on today's tiles |
| #52 One shell for all three views | todo | | | | |
| #53 Stat cards with delta and trend spark | todo | | | | |
| #54 What: ledger card-table, badges, help popover | todo | | | | |
| #55 How: runs as cards, stage panels, off-script card | todo | | | | |
| #56 Where: sections as cards | todo | | | | |
| #57 Re-derive DESIGN.md, retake screenshots | human | | | | excluded: public screenshots, documenter, public push |

## Owed

## Decisions
- sitting: ten build contracts — ADR-0030 (done)
- #51: --o-radius-card in :root only (shape is theme-invariant, ADR-0017 §3) — ADR? no
- #51: block-agreement test checks every token, not only the new ones — ADR? no

## Blocked

## Nits
- #51: floor-check role regex `(\w+)` skips a hyphenated role (`--o-info-x-fill`); use `(\w[\w-]*)`
- #51: floor-check asserts are bare `assert`, stripped under `python -O`; self.fail/ValueError sturdier
- #51: DESIGN.md still says 28px stat numerals — re-derived in #57
