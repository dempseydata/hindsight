# ADR-0028: The header visual is per view — session heat on what, tokens on where — over one shared selection, a set of days

**Date:** 2026-09-18 · **Status:** accepted · **Decides:** [issue #35](https://github.com/dempseydata/hindsight/issues/35) (grilling, 2026-09-18); the errors tile in [#36](https://github.com/dempseydata/hindsight/issues/36) rode along · **Touches:** ADR-0004, ADR-0007, ADR-0009, ADR-0014

## Context

Ticket #44 gave both views one header: project chips, window presets, and a stacked per-day token chart whose bars are the time filter — click a day, click a second for a range, click again to deselect. The chart is the where view's grain (tokens) sitting above the what view's grain (sessions and what they did). On the what view it answers a question the ledger does not ask, and the two-click range was clunky on both.

What the what view wants above the ledger is a GitHub-style contribution heatmap: a year at a glance, one cell per local day (ADR-0014), hue by how much happened. Two questions fell out of asking for it.

- **What keys the hue.** The instinct was a combined did / decided / ADR score. Colour carries one ordinal well; a composite needs weights nobody can defend, and it depends on the audit having run, so a synced-but-pending session would read as a dead day — the coverage-honesty rule broken on the front page.
- **What a click means.** A heatmap invites picking days that are not adjacent. Today's selection is a range (`tFrom`/`tTo`), shared across what ↔ where through sessionStorage. A set on one view and a range on the other cannot round-trip.

## Decision

1. **The header visual is per view; the filter state is not.** `chrome.js` keeps chips, presets, the selection and the mount; each view supplies the visual: a session heatmap on what, the token chart on where. Each view's header shows its own grain. The serve.py docstring's "shared … token chart" is corrected.
2. **Heat keys to one count, and the tiles choose it.** Four metric tiles sit under the heatmap — Sessions, Actions, Decisions, ADRs — over the visible window, and they are a radio group: the pressed tile keys the heat. Default Sessions, the one count the substrate knows without the model. No composite, no weights. The tooltip carries all four.
3. **The heatmap follows the ledger rule.** A session counts on every local day it had usage (#9's rule); actions, decisions and ADRs count on the session's first day, where the entry lives. The heatmap and the ledger agree on which days are empty, under any project filter — the same invariant `what_data` already states for the chart.
4. **Selection is a set of days, on both views.** Click toggles a day; shift-click adds a contiguous range from the last-clicked day; a preset or **clear** empties the set. The where view's bars adopt the same, and the two-click range is gone. One model, one predicate: the set when non-empty, else the preset range.
5. **The ramp is the existing ink ramp.** `--o-ink-1..4` is a four-step sequential scale in both themes (ADR-0007, re-tuned by ADR-0017), which is exactly a heatmap's four levels plus empty. No new tokens; chart data ink stays on its own palette, and the accent stays off it.
6. **Vocabulary: Actions and Decisions at render.** The tile could not say Actions while the ledger row said *did*. Rendered text and CONTEXT.md move to Actions / Decisions. The stored section headers (`**Did:**`, `**Decided:**`) and the what-pass prompt stay: the prompt is under the eval gate (ADR-0016) and the format is ADR-0004's; renaming them is a format decision, not a view one, and is not taken here.

## Alternatives rejected

- **A composite score for the hue.** See the context: undefendable weights, and pending reads as nothing.
- **A second visual channel for ADRs** (a dot or corner mark on the cell). Two channels on a 12px cell; the radio tile gives ADRs the whole ramp on demand instead.
- **The heatmap on both views.** Tokens per day in a heatmap loses the stacked segments the hide-cache-reads toggle acts on; the where view keeps the chart that shows its grain.
- **A set on what, a range on where.** Cannot round-trip through the shared state; one model or none.
- **Range by two clicks, kept.** The behaviour being replaced.

## Consequences

- One build ticket (#35): heatmap and tiles in what.js, the selection set in chrome.js, the token chart relocated to where.js, tile CSS promoted to chrome.css, vocabulary at render, tests, DESIGN.md re-derived, screenshots retaken.
- The hide-cache-reads toggle stays in the header and does nothing on the what view. Accepted; it is a header control, and moving it is more chrome divergence than it saves.
- Hue by a fifth count later is one more tile, not a new decision. A per-project row in the heatmap, or any second surface, is a new surface and runs the Design flow.
