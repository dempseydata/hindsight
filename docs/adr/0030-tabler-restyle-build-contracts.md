# ADR-0030: Tabler restyle — build contracts fixed before the unattended build

**Date:** 2026-09-30 · **Status:** accepted · **Decides:** the decision sitting before the night-shift build of [#50](https://github.com/dempseydata/hindsight/issues/50) (tickets #51–#57) · **Amends:** ADR-0029 (trend-spark zeros)

## Context

ADR-0029 and the spec leave contracts open that several tickets share: markup one ticket produces and the next consumes, and three places where the sources contradict the code. A prescan found ten; the operator settled each before the build, so no implementer invents one alone.

## Decision

1. **Nav.** The shell keeps the nav inside a `<header>` element with hrefs exactly `/what`, `/where`, `/how` — the control sync's `header nav a[href^="/how"]` lookup and its test stay as they are.
2. **Icons.** The icons asset defines `const ICONS = {name: path}`, keyed by Tabler's glyph names (`route-slash` for Off-script). Markup — Python-built, the static `where.html`, and JS-built alike — carries `data-icon="<name>"` placeholders; a small shell script fills them with inline SVG and hides the fallback text (`?`, `▲▼`) once the glyph shows.
3. **Class names are Hindsight's, `o-`-prefixed like the tokens.** Card: `.o-card`, `.o-card-head`, `.o-card-title`, `.o-card-sub`, `.o-card-actions`, `.o-card-body`; `.o-card-table`; `.o-stage-panel`. Stat card: `.o-stat-card`, `.o-delta`, `.o-trend-spark` (the existing bar spark keeps `svg.spark`). Badge: `.o-badge` with `.o-ok` / `.o-caution` / `.o-problem` / `.o-neutral`. Chrome: `.o-topbar`, `.o-navrow`, `.o-page-head`, `.o-pretitle`, `.o-page-title`, `.o-page-desc`, `.o-actions`, `.o-page-body`. Help: `.o-help` (the button) and `.o-pop` (the popover). Today's classes that survive unchanged (`.note`, `.cov`, …) keep their names.
4. **Help popover: the platform's `popover` attribute** with a `popovertarget` button — no JS for open, close, Esc or click-outside. Notes the views fill by id keep their ids inside the popover. **Any sentence stating a coverage gap or a capture start stays visible** under the card title; only explanation moves behind the `?`. Where's overall coverage line (`#wcov`) stays a visible line at the top of the page body, after the chips.
5. **What's `?`** sits on the "Sessions per day" card and carries ADR-0028 §3's counting rule verbatim. The hint stays the card's subtitle.
6. **The contract is amended, not bypassed.** `--o-stat-size` becomes 24px, labelled the stat-card value; `--o-radius-card: 8px` is added and `--o-radius` is relabelled stage panels; the floor comment admits badge text in its `-on` weight on a filled badge. The spec's "no existing token value changes" is corrected accordingly.
7. **Trend-spark zeros** (amends ADR-0029 §6, whose reason — "every stat card counts sync-derived data" — was wrong). Days before the first synced day are a gap on every stat card. On the three analysis-derived cards (Actions, Decisions, ADRs), a day whose sessions are all pending is a gap too. Elsewhere zero is zero. The dim line keeps stating what is awaiting analysis or unrecoverable.
8. **Delta.** A rounded percent; `—` unless the prior window is non-zero and lies wholly inside the synced range; no arrow at 0%. Today's tile extras ("N awaiting analysis · N unrecoverable", "+n unknown", "% of tokens") move to a dim line under the value.
9. **Breakage tier badges:** `problem` on the problem fill, `informational` on the ok fill — red pairs with blue, as the banners do today.
10. **A card-table is a visual grammar, not an element.** What's ledger and where's league keep their `<details>` rows, styled as a card-table grid; the session anchor (ADR-0023), the open-row handling and their tests are untouched.

## Consequences

- ADR-0029 carries a pointer amendment for §6.
- Every implementer brief in the build carries this ADR as a binding source, ahead of the spec.
