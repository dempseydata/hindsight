# #45 What-view: the styled session ledger

state: closed · labels: wayfinder:task · opened: 2026-08-20 · closed: 2026-08-25

Part of #40

## Question

Build the styled what-view on the server + chrome: one collapsed row per session (date · title · n did · n decided · n ADR) expanding to the full Did / Decided / Setup-changes entry; project chip on every row; one cross-project stream; day roll-up as render-time grouping only; ADR count mechanical.

Judge against real data and record: does the ADR-count badge earn its row space? How do zero-decision sessions (~half of all) read?


---

**comment · 2026-08-25**

**Resolved.** Commit 157011a — the what-view is live on `/what`, mounted on #44's chrome via `hs.onFilter`; 12 tests green, interactions verified in a live browser against the real DB (250 sessions).

**Built, as specified** — one collapsed row per session (project chip · title · `n did · n decided` · ADR badge), expanding via native `<details>` to the full Did / Decided / Setup-changes entry; one cross-project stream filtered by chips and time window; day roll-up is render-time grouping only (day headers, newest first); ADR count read mechanically from `audit.adr_count`, never model text. Entries are parsed server-side (`parse_entry`) into title + sections; both corpus shapes handled — bullet sections (149 entries) and paragraph sections with semicolon-separated clauses (5 entries, kept whole for display, clauses counted for the row). Section names are pinned to ADR-0004's locked format, noted in the docstring.

**Judgement 1 — the ADR badge earns its space only as a conditional badge, not a column.** On real data 7 of 240 sessions have a nonzero count (4×1, 2×2, and one 15 — the ccwhy ADR blitz, which the badge makes pop exactly as an audit surface should); 76 are known-zero and 157 unknown (pruned transcripts, NULL). A standing column would be blank on 97% of rows. Adopted: an accent-bordered `n ADR` badge renders only when ≥ 1; known-zero and unknown both render nothing — no number is asserted, so the unknown/zero distinction isn't misstated, and every number shown is the trustworthy mechanical one.

**Judgement 2 — zero-decision sessions read as three distinct dim populations, and the ledger stays scannable.** Of ~half the corpus with no decisions: 57 SKIP sessions render as dim one-liners ("trivial session — skipped", no expansion); 29 #38 refusal rows render dim ("no entry — the model refused this session (defect #38)") with the raw text in the expansion — tolerated verbatim, never repaired here; 12 well-formed entries without a Decided section read "n did · 0 decided", which is honest and unobtrusive. Dim rows compress visually, so the default 14-day window and even the all-time view scan cleanly; the month fits ~2 screens as the greybox promised.

**Beyond spec, forced by real data** — the DB had grown to 250 sessions while `audit` stops at 08-17: analyzed-only rows would have silently dropped 10 sessions the coverage line counts. `what_data` now LEFT JOINs from `sessions`, rendering synced-but-unanalyzed sessions as dim "synced, not yet analyzed — run an analysis" rows, counted in the view summary ("N awaiting analysis"). Same honesty for undated sessions: they can't be windowed, so they always render (under "undated") rather than vanishing beneath a preset. Scratch-dir path names get truncated chips (ellipsis + full name in the tooltip).

**Pre-commit review riders** — fixed in this diff: quote-safe JS escaping (esc output lands in a `title` attribute), AA contrast for small text (`--o-faint` → `--o-dim` for `.note`/`#ctl`/counts/dim titles — faint measured 3.99:1 on panel, below the floor), long-form line-height on the refusal `pre` (the `font:` shorthand had reset it), one shared `_blob()` for script-embedded JSON before #48 adds a third copy. Residue in #44's committed chrome (chart range anchored to session start dates, empty-DB RangeError, listener-created-DB 500s, zero-token chip degenerate, smaller quality items) is appended to #50; the 9px chart-axis contrast call is flagged there for #47's floor audit. Efficiency caching was declined: render on 250 real sessions is instant, and ADR-0008's live-read simplicity stands at this scale.


