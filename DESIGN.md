---
name: Hindsight
description: Local observability over Claude Code history — an indigo instrument deck for one operator, in a dark and a light theme.
# Values below are the dark theme (the :root base in design/tokens.css).
# Light-theme values live in tokens.css's light blocks and in the sidecar.
colors:
  bg: "#0b0d14"
  panel: "#141826"
  border: "#272e45"
  text: "#dde2f0"
  dim: "#9aa3bd"
  faint: "#6f7794"
  accent: "#7c9bff"
  accent-ink: "#0b0d14"
  compare: "#f0b23f"
  ok: "#7c9bff"
  ok-text: "#a3b8ff"
  caution: "#e3b859"
  caution-text: "#eac878"
  problem: "#f27878"
  problem-text: "#f79b9b"
  ink-1: "#82a9e8"
  ink-2: "#5c83c4"
  ink-3: "#41639b"
  ink-4: "#2b4468"
  spark: "#82a9e8"
  gapline: "#4c5470"
  axis: "#6f7794"
  stage-1: "#2fc4c4"
  stage-2: "#a98cf5"
  stage-3: "#e07ad8"
  stage-4: "#f0995a"
  stage-5: "#d4c95a"
  stage-off: "#6f7794"
typography:
  title:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "15px"
    fontWeight: 600
  body:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  stat:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.25
  data:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
  label:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "10px"
    fontWeight: 600
    letterSpacing: "0.05em"
rounded:
  panel: "6px"
  control: "2px"
spacing:
  gap-sm: "0.35rem"
  gap-md: "0.6rem"
components:
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "0.9rem 1.1rem"
  stat-tile:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "0.55rem 1rem 0.5rem"
    width: "min-width 7rem"
  chip-button:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.dim}"
    rounded: "{rounded.control}"
    padding: "0.2rem 0.55rem"
  chip-button-on:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "0.2rem 0.55rem"
  project-chip:
    textColor: "{colors.dim}"
    rounded: "{rounded.control}"
    padding: "0.05rem 0.4rem"
    typography: "{typography.label}"
  adr-badge:
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "0 0.3rem"
  theme-toggle:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.dim}"
    rounded: "{rounded.control}"
    padding: "0.2rem 0.55rem"
---

<!--
DERIVED DOCUMENTATION — generated from the shipped artifact (build/serve.py +
design/tokens.css) for Impeccable's tooling. design/tokens.css remains the sole
authoritative direction contract; the server inlines it into every page at
render time. On any conflict between this file and tokens.css, tokens.css wins.
Re-derive this file (re-run the documenter) whenever tokens.css or the UI's
visual system changes. Derived 2026-08-31 from the post-light-theme surface
(ticket #83, ADR-0017).
-->

# Design System: Hindsight

## Overview

**Creative North Star: "The Indigo Deck"**

Hindsight is an observability workhorse in the Grafana/Honeycomb lineage, with one graft from the terminal-instrument family: bar sparklines rather than heat strips (V3 · Indigo deck, ADR-0007). It now ships two themes from one token contract (ADR-0017): the dark deck — near-black indigo ground carrying elevated panels — remains the incumbent `:root` base, and a light derivation ("C · Ledger") keeps the same hues and roles on an inverted value structure: white ground, recessed indigo panels, borders over elevation. System preference decides the theme by default; a three-state header toggle (system → light → dark) pins it per browser, applied before first paint. A single periwinkle-family accent marks the active and the interactive; everything numeric sits in the system monospace with tabular figures. The whole surface is server-rendered HTML with inline SVG charts — zero dependencies, no imagery, no runtime font fetches.

The system's second personality trait is honesty grammar: missing data is drawn as absence, never as zero. A day without data is a gap in the chart, an unknown value is an em-dash, unpaired calls read "+n?", and pre-coverage regions of a spark are shaded. The visual language is built to make "unknown" and "zero" impossible to confuse.

**Key Characteristics:**
- Dense, data-first: 13px body, 10–12px monospace labels and figures, 28px stat numerals.
- Two themes, one contract: every token holds a value in both; view code is theme-blind and identical under each.
- One accent (periwinkle family) used sparingly for interaction and state; the amber family reserved for selection/compare.
- Titled panels; per-day bar sparks on one shared 30-calendar-day axis.
- Every colour on screen is a `var(--o-*)` token from `design/tokens.css`; no literals in view code.

## Colors

One set of roles, two value sets: dark is a near-black indigo ground with cool blue-grey text tiers, one periwinkle voice, and a desaturated blue ink ramp; light keeps every hue family and deepens it for contrast on a white ground. The light set was floor-verified before acceptance: worst text contrast 5.18:1 at rendered sizes, every stage hue ≥6.5:1 on the light panel (ADR-0017). Values below read dark · light.

### Primary
- **Periwinkle** (`--o-accent`, #7c9bff · #2f4fc9): the single interactive voice — links, the current nav item, chip on-state text and border, the ADR badge, the `now` run badge. Never body text, never a fill on a large surface. `--o-accent-ink` (#0b0d14 · #ffffff) is the reserved on-accent ink; the shipped UI never fills a surface with accent, so it currently has no call site.
- **Compare Amber** (`--o-compare`, #f0b23f · #956609): the selection/compare hue — the selected chart column wash at `--o-wash-sel` (0.06 · 0.12 fill-opacity) and the selection rule at `--o-wash-rule` (0.7 · 1). Nothing else.

### Semantic
Text in a semantic role always renders in the `-text` weight (AA on panel); the bright weight is for non-text marks.
- **Signal Blue** (ok: `--o-ok` #7c9bff · #2f4fc9 / `--o-ok-text` #a3b8ff · #2c49bd): the "fine" pole — shipped usage is inline `code` in ledger entries (`--o-ok-text`). Deliberately blue, not green.
- **Caution Amber** (`--o-caution` #e3b859 · #a87d08 / `--o-caution-text` #eac878 · #846007): the stale-warning role — the dashed `warn` border (bright weight) with its text and code in the `-text` weight; `stale` markers in the how-view.
- **Problem Red** (`--o-problem` #f27878 · #c23c3c / `--o-problem-text` #f79b9b · #ac3232): error counts in tables (`.err`, `-text` weight) and the errors-per-day bars beneath call sparks (bright weight, non-text mark).

### Chart Ink
Data volume never borrows the accent or semantic hues; it has its own desaturated blue ramp. The ramp orders by contrast against the panel, not by lightness: ink-1 is always the most visible step, so it is the lightest in dark and the darkest in light.
- **Ink 1–4** (#82a9e8 → #2b4468 dark · #24406e → #b9c4dd light): the stacked token-chart segments (input / output / cache-create / cache-read), highest-contrast first.
- **Spark Blue** (`--o-spark`, #82a9e8 · #24406e): all sparkline call bars.
- **Gapline** (`--o-gapline`, #4c5470 · #ccd2e2): non-text chart furniture — shipped as the pre-coverage shading on OTEL-fed sparks at `--o-wash-precov` (0.22 · 0.35 opacity).
- **Axis** (`--o-axis`, #6f7794 · #a0a8be): reserved for non-text chart lines only, in both themes. Axis *text* renders in `--o-dim` — the dark value is 3.99:1 on panel, below AA for text (floor audit, ticket #47).

### Stage Identity
A categorical palette for the how-view: which declared stage a stated-process card or phase-run band belongs to. Carried only by the 3px left border of `.stage` and `.run` panels (via an inline `--stage` custom property); labels stay `--o-text`, so no `-text` weight exists.
- **Stage 1–5** (`--o-stage-1..5`: Teal #2fc4c4 · #096060, Violet #a98cf5 · #6137c5, Magenta #e07ad8 · #922a82, Orange #f0995a · #8a4209, Gold #d4c95a · #61570d): assigned positionally — a declaration's stages take 1..5 in declared order and cycle past five. Identity is per project, not per stage name. Light values deepen each hue to hold ≥6.5:1 on the light panel.
- **Stage Off** (`--o-stage-off`, #6f7794 · #525a74): the fallback rule for off-script, unbucketed, and undeclared cards.
The current run is marked with a small accent `now` badge, not an accent rule, so the rule is free to carry the stage.

### Neutral
- **Ground** (`--o-bg`, #0b0d14 · #fcfcfe): page background; also the recessed background of open detail rows inside panels.
- **Panel** (`--o-panel`, #141826 · #f1f3f9): every elevated (dark) or recessed (light) surface — panels, tiles, rows, chips, the header chart.
- **Border** (`--o-border`, #272e45 · #d9dde9): all borders, dividers, and table rules.
- **Text** (`--o-text`, #dde2f0 · #14182a): primary text.
- **Dim** (`--o-dim`, #9aa3bd · #4a5169): secondary text — notes, labels, table heads, counts, axis text.
- **Faint** (`--o-faint`, #6f7794 · #767e98): the quietest tier; shipped as the ledger row's hover border.

### Named Rules
**The One-Contract Rule.** Both themes live in `design/tokens.css` and nowhere else: dark verbatim in `:root`, light behind `@media (prefers-color-scheme: light)` guarded `:root:not([data-theme="dark"])`, plus explicit `[data-theme="light"]` / `[data-theme="dark"]` pin blocks. A new token lands in all four blocks; the two light blocks stay identical; view code never branches on theme.
**The Token-Only Ink Rule.** Every colour renders via a `var(--o-*)` token from tokens.css. View code contains no colour literals; the only non-token paint is `transparent` on hit-target rects. Theme-sensitive opacities go through the wash tokens (`--o-wash-sel` / `--o-wash-rule` / `--o-wash-precov`), never literals.
**The Red-With-Blue Rule.** The ok pole is periwinkle blue, never green; red pairs with blue (Few). Nothing in the system is green — in either theme.
**The Own-Ink Rule.** Chart volume ink comes only from the ink/spark tokens — never accent, never compare. The one semantic colour permitted in a chart is `--o-problem`, and only for the error series drawn beneath its calls spark.
**The Stage-Rule Rule.** Stage hues are non-text marks only (left rules, dots), positional per declaration, never chart ink and never a stand-in for ok/caution/problem; conversely ink and semantic tokens never key a stage.

## Typography

**Body Font:** system-ui (with 'Helvetica Neue', sans-serif)
**Data/Label Font:** ui-monospace (with 'SF Mono', Menlo, monospace)

**Character:** Zero-fetch system faces, identical in both themes — faces, shape, and motion are theme-invariant and live in `:root` alone. The sans carries prose and titles; the monospace carries everything that is a datum — numerals, labels, chips, axis text — always with `font-variant-numeric: tabular-nums` where columns of figures align.

### Hierarchy
- **Stat** (600, 28px `--o-stat-size`, 1.25, mono, tabular-nums): stat-tile numerals only. The largest type on any screen.
- **Title** (600, 15px): the `h1` wordmark. The measured-median figure in the sunk-cost panel reuses this size in mono (600, 15px).
- **Panel heading** (bold, 13px): `h2` panel titles, same size as body — hierarchy by weight and position, not size.
- **Body** (400, 13px, 1.5): default prose and ledger entry text.
- **Data** (400, 12px, mono): table cells, numeric columns, code, raw-entry `pre` (1.5 line-height on multi-line).
- **Label** (600, 10–11px, mono, 0.05em, UPPERCASE): section heads inside entries, table headers, league grid headers. Non-uppercase 11px mono: day headings, counts, chip buttons, the theme toggle; 10px: project chips; 9px: chart axis text.

### Named Rules
**The Mono-Datum Rule.** If it is a number, a label over data, or an identifier, it is monospace; if it is prose, it is the sans. Numerals in columns always carry tabular figures.

## Layout

Single-column, full-width, dense. Body padding 1.1rem 1.4rem 2rem; `main` sits 1.1rem below the shared header chrome (wordmark + nav inline, theme toggle floated right, coverage line, project-chip row, window controls, scrollable token chart). Panels stack vertically with 1rem top margins; stat tiles flex-wrap with 0.6rem gaps (min-width 7rem per tile); chip rows flex-wrap at 0.35rem gaps. Panel interior padding is 0.9rem 1.1rem. Tables are full-width, collapsed borders, 12px, with row rules in `--o-border` and no rule after the last row. The consumer league uses a six-column grid (`minmax(9rem,1fr) 128px 3.5rem 3rem 4.5rem 4.5rem`). Wide charts scroll horizontally inside their panel (`overflow-x: auto`), newest day at the right. The how-view's two-column grids collapse to one column below 760px; everywhere else one layout serves every width, with flex-wrap and scroll absorbing narrowness.

## Elevation & Depth

Per theme. Dark is a hybrid: tonal layering (panel over ground) plus one shared ambient shadow — panels and stat tiles sit on `--o-panel` with a `--o-border` border and the single elevation token `--o-elev` (`0 3px 10px rgba(0, 0, 0, 0.45)`). Light is flat by contract: `--o-elev: none`, borders over elevation, with the indigo panels reading as recessed fields on the white ground. In both themes depth also runs inward: an open detail row's summary and body recess to `--o-bg`, reading as a well cut into the panel. Motion is one token, `--o-motion` (200ms ease): where-view panels lift `translateY(-1px)` on hover (transform + box-shadow transition; in light only the transform is visible); what-view ledger rows brighten their border to `--o-faint` instead — the flat surface's hover.

### Shadow Vocabulary
- **Elevation** (`--o-elev`: `box-shadow: 0 3px 10px rgba(0, 0, 0, 0.45)` dark · `none` light): the only shadow. Panels and stat tiles at rest.

### Named Rules
**The One-Shadow Rule.** There is exactly one shadow token, and only the dark theme populates it. New surfaces either carry `--o-elev` or are flat; no bespoke shadows, and never a shadow that exists only in light.

## Shapes

Two radii, strictly assigned and theme-invariant: 6px (`--o-radius`) for panels, tiles, ledger rows, and the header chart container; 2px for everything chip-sized — chip buttons, project chips, the ADR badge, the theme toggle. Borders are 1px `--o-border` everywhere. Native `<details>/<summary>` provides all expansion, with the marker suppressed; charts are inline SVG rectangles — bars only, no curves, no rounded bar caps.

## Components

### Chip Buttons (project chips, window presets, league category chips)
- **Style:** 11px mono `--o-dim` on `--o-panel`, 1px `--o-border` border, 2px radius, padding 0.2rem 0.55rem, cursor pointer.
- **On state:** text and border switch to `--o-accent`; background unchanged.
- **Checkbox:** the hide-cache-reads toggle uses `accent-color: var(--o-accent)`.

### Theme Toggle
- **Style:** the chip-button treatment floated right in the header — 11px mono `--o-dim` on `--o-panel`, 1px `--o-border`, 2px radius, padding 0.2rem 0.55rem. Label reads `theme: system|light|dark`.
- **Behavior:** cycles system → light → dark. The pin lives in `localStorage` per browser and is applied as `data-theme` on `<html>` by an inline script in `<head>` (build/assets/theme.js) before first paint — a pinned page never flashes the other theme. The server stores nothing per viewer.

### Project Chip (inline identifier)
- **Style:** 10px mono `--o-dim`, 1px `--o-border` border, 2px radius, padding 0.05rem 0.4rem; max-width 14rem with ellipsis. Non-interactive; identifies a project or type inside rows.

### ADR Badge
- **Style:** `--o-accent` text and 1px accent border, 2px radius, padding 0 0.3rem — accent outlining content, marking "this session wrote an ADR"; the how-view's `now` run badge reuses the treatment at 10px.

### Panels
- **Corner Style:** 6px (`--o-radius`).
- **Background / Border / Shadow:** `--o-panel` / 1px `--o-border` / `--o-elev` (dark only; flat in light).
- **Heading:** 13px `h2`, then an 11px `--o-dim` note paragraph explaining the panel's honesty caveats.
- **Hover (where-view):** `translateY(-1px)` lift over `--o-motion`.

### Stat Tiles
- **Style:** panel treatment at padding 0.55rem 1rem 0.5rem, min-width 7rem; a 28px/1.25 600 mono tabular numeral over an 11px `--o-dim` label.

### Ledger Rows (what-view)
- **Style:** native `<details>` styled as a 6px-radius bordered row on `--o-panel`; summary is a flex line of project chip · title · counts. Hover shifts border to `--o-faint` over `--o-motion`. Dim one-liners (`--o-dim` title) mark trivial/pending/defect rows.

### Tables
- **Style:** 12px, full-width, collapsed; headers 10px 600 mono UPPERCASE 0.05em `--o-dim` with a `--o-border` bottom rule; numeric cells right-aligned 12px mono tabular-nums; errors in `--o-problem-text`; unknowns as `--o-dim` em-dashes.

### Sparklines (signature component)
- **Grammar:** per-day bars on the shared 30-calendar-day axis ending at the last synced day; 3px bars, 1px gaps, 14px tall (own peak per spark; minimum bar height 1px). A missing day is a gap, never a zero-height bar.
- **Error series:** when errors exist, a second 6px-tall red (`--o-problem`) band renders 2px beneath the calls band, on its own peak.
- **Coverage shading:** OTEL-fed sparks shade the pre-coverage region with `--o-gapline` at `--o-wash-precov` opacity — capture didn't exist yet, not zero activity.
- **Header chart:** the same grammar scaled up — 14px bars, 3px gaps, 96px tall, stacked in ink-1…ink-4; axis labels 9px mono in `--o-dim` every 7th day; selection washes the column in `--o-compare` at `--o-wash-sel` with a 2px compare rule beneath at `--o-wash-rule`.

## Do's and Don'ts

### Do:
- **Do** render every colour via a `var(--o-*)` token; tokens.css is inlined into every page and is the only place a colour value lives.
- **Do** land any new token in all four blocks of tokens.css — dark `:root`, the light media block, and both pin blocks — and keep the two light blocks identical.
- **Do** use the `-text` weight whenever a semantic colour carries text; the bright weight is for marks (spark bars, rules, the warn border).
- **Do** route theme-sensitive opacities through the wash tokens (`--o-wash-sel` / `--o-wash-rule` / `--o-wash-precov`); a wash that reads on near-black disappears on white.
- **Do** draw absence as absence: missing day = gap, unknown value = em-dash in `--o-dim`, unpaired = "+n?", pre-coverage = shaded region. Never render an unknown as zero.
- **Do** keep sparks on the shared 30-calendar-day axis with their own peak, and put figures in monospace with tabular-nums.
- **Do** pair each panel with a dim note stating its coverage caveats — the honesty prose is part of the component.

### Don't:
- **Don't** branch on theme in view code or assets; views are theme-blind. Theme is decided entirely by tokens.css plus the pre-paint pin in theme.js.
- **Don't** introduce green; the ok pole is periwinkle blue and red pairs with blue, in both themes.
- **Don't** put the accent on body text or large surfaces — it marks interaction and state only.
- **Don't** use accent, compare, or semantic hues for chart volume ink; volume is ink/spark only (the error series in `--o-problem` is the sole semantic chart mark).
- **Don't** set axis or other sub-AA text in `--o-axis`; chart text uses `--o-dim` (ticket #47). `--o-axis` is for non-text chart lines, in both themes.
- **Don't** set text in a stage hue or key a stage to an ink/semantic token; stage colour lives on rules only.
- **Don't** add shadows in the light theme — light conveys depth with borders and recessed panels (`--o-elev: none` is the contract, not an omission).
- **Don't** fetch fonts, load imagery, or add dependencies; the surface is system faces, inline SVG, and one inline stylesheet.
