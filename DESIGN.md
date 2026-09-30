---
name: Hindsight
description: Local observability over Claude Code history — Tabler's layout and card grammar on the indigo deck's palette, for one operator, in a dark and a light theme.
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
  ok-fill: "#7c9bff"
  ok-on: "#0b0d14"
  caution: "#e3b859"
  caution-text: "#eac878"
  caution-fill: "#e3b859"
  caution-on: "#0b0d14"
  problem: "#f27878"
  problem-text: "#f79b9b"
  problem-fill: "#f27878"
  problem-on: "#0b0d14"
  neutral-fill: "#6c7491"
  neutral-on: "#ffffff"
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
  page-title:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.4
  card-title:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "16px"
    fontWeight: 500
  brand:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "15px"
    fontWeight: 600
  body:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  caps:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "11px"
    fontWeight: 500
    letterSpacing: "0.04em"
  badge:
    fontFamily: "system-ui, 'Helvetica Neue', sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.6
  stat:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "24px"
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
  card: "8px"
  panel: "6px"
  control: "2px"
spacing:
  gutter: "12px"
  card-gap: "16px"
  card-pad: "20px"
  section: "24px"
  cell: "0.75rem"
  gap-sm: "0.35rem"
components:
  top-bar:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    typography: "{typography.brand}"
    height: "56px"
  nav-item:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.dim}"
    padding: "0 0.75rem"
    height: "56px"
  nav-item-current:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    padding: "0 0.75rem"
    height: "56px"
  card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
    padding: "20px"
  card-head:
    textColor: "{colors.text}"
    typography: "{typography.card-title}"
    padding: "0.75rem 20px"
    height: "65px"
  card-table-head:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.dim}"
    typography: "{typography.caps}"
    padding: "0.5rem 20px"
  stage-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.panel}"
    padding: "0.9rem 1.1rem"
  stat-card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
    padding: "20px"
  badge-ok:
    backgroundColor: "{colors.ok-fill}"
    textColor: "{colors.ok-on}"
    typography: "{typography.badge}"
    rounded: "{rounded.panel}"
    padding: "0 0.4rem"
  badge-caution:
    backgroundColor: "{colors.caution-fill}"
    textColor: "{colors.caution-on}"
    typography: "{typography.badge}"
    rounded: "{rounded.panel}"
    padding: "0 0.4rem"
  badge-problem:
    backgroundColor: "{colors.problem-fill}"
    textColor: "{colors.problem-on}"
    typography: "{typography.badge}"
    rounded: "{rounded.panel}"
    padding: "0 0.4rem"
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
  theme-toggle:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.dim}"
    rounded: "{rounded.control}"
    padding: "0.2rem 0.55rem"
  help-popover:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
    padding: "12px 16px"
  breakage-banner-problem:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.problem-text}"
    rounded: "{rounded.panel}"
    padding: "0.55rem 0.9rem"
  breakage-banner-informational:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ok-text}"
    rounded: "{rounded.panel}"
    padding: "0.55rem 0.9rem"
  error-group:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    typography: "{typography.data}"
    padding: "0.1rem 0"
---

<!--
DERIVED DOCUMENTATION — generated from the shipped artifact (build/serve.py,
build/assets/, design/tokens.css) for Impeccable's tooling. design/tokens.css
remains the sole authoritative direction contract; the server inlines it into
every page at render time. On any conflict between this file and tokens.css,
tokens.css wins. Re-derive this file whenever tokens.css or the UI's visual
system changes. Re-derived 2026-09-30 from the Tabler layout and card-grammar
restyle (spec #50, ADR-0029, ADR-0030; tickets #51–#56), including the
post-shift change that puts record badges on the ok role.
-->

# Design System: Hindsight

## Overview

**Creative North Star: "The Indigo Deck"**

Hindsight is an observability workhorse in the Grafana/Honeycomb lineage. Since ADR-0029 it is a mix, chosen strand by strand on real data: **Tabler's layout and card grammar, on the Indigo deck's palette**. Tabler is a reference, not a dependency — nothing is vendored; its shell, cards, card-tables, stat cards, filled badges, help popovers and icon set were ported by hand into `design/tokens.css` and `build/assets/`. The palette, type, and honesty grammar are the incumbent deck's (ADR-0007): near-black indigo ground, elevated panels, one periwinkle voice, system faces, bar sparks on a shared 30-day axis. Two themes ship from one token contract (ADR-0017): the dark deck is the `:root` base; the light "C · Ledger" derivation keeps every hue and role on a white ground with recessed panels and borders over elevation. The surface is server-rendered HTML with inline SVG charts and inline SVG glyphs — no dependencies, no imagery, no webfont, no runtime font fetches.

Two chassis carry everything, on purpose (ADR-0029 §4): the **card** (8px) holds data; the **stage panel** (6px, 3px stage-hue left rule) marks stage identity. The radius is the only structural difference between them. No density trim was taken — Tabler's 20px card padding and 65px card headers were measured against the old deck and kept, knowing the pages grow.

The system's second trait is honesty grammar: missing data is drawn as absence, never as zero. A day without data is a gap in a bar spark, an unknown value is an em-dash, unpaired calls read "+n?", pre-coverage regions are shaded, and a trend spark breaks before the first synced day and across unselected days. Any sentence stating a coverage gap stays visible under its card title; only explanation moves behind a help `?`.

**Key Characteristics:**
- Tabler horizontal shell: 56px top bar, 56px nav row, page header, 1320px container.
- Two chassis: card (8px, ruled 65px header, 20px body) for data; stage panel (6px, 3px stage rule) for stage identity.
- Dense data type: 13px body, 11–12px monospace figures, 24px stat-card values, uppercase 10–11px labels.
- One accent (periwinkle) for interaction and current state; amber reserved for selection; status carried by filled badges in the ok / caution / problem roles.
- Every colour on screen is a `var(--o-*)` token from `design/tokens.css`; no literals in view code.

## Colors

One set of roles, two value sets: dark is a near-black indigo ground with cool blue-grey text tiers, one periwinkle voice, and a desaturated blue ink ramp; light keeps every hue family and deepens it for contrast on a white ground. Values below read dark · light. Every `-text` weight and every fill/on pair clears AA in both themes (fill/on pairs: ok 7.38 · 6.81, caution 10.41 · 4.69, problem 7.15 · 5.24, neutral 4.62 · 4.61).

### Primary
- **Periwinkle** (`--o-accent`, #7c9bff · #2f4fc9): the single interactive voice — links, the nav row's 2px current-view rule, chip-button on-state text and border, the 2px top bar on the pressed stat card, focus rings and strokes, the checkbox `accent-color`, and underlined link-buttons inside notes. Never body text, never a large fill. `--o-accent-ink` (#0b0d14 · #ffffff) is the reserved on-accent ink; nothing fills a surface with accent, so it has no call site.
- **Selection Amber** (`--o-compare`, #f0b23f · #956609): selection only — the selected token-chart column wash at `--o-wash-sel` (0.06 · 0.12) with its selection rule at `--o-wash-rule` (0.7 · 1), and in-window heatmap cells at four opacities (0.3 · 0.55 · 0.8 · 1), an empty in-window day at `--o-wash-sel`.

### Semantic
Each role has three weights: the bright weight for non-text marks, the `-text` weight for text on a surface, and a `-fill` / `-on` pair for filled badges.
- **Signal Blue** (ok: `--o-ok` #7c9bff · #2f4fc9 / `--o-ok-text` #a3b8ff · #2c49bd / `--o-ok-fill` #7c9bff · #2f4fc9 on `--o-ok-on` #0b0d14 · #ffffff): the "fine" pole, deliberately blue. Text weight: inline `code` in ledger entries, the informational breakage banner, the falling delta on a cost card. Fill: the `empty` and `trivial` status badges, the `now` run badge, the `informational` tier badge — and every record badge (project, continuation, subagent count, ADR count, type and category badges on where).
- **Caution Amber** (`--o-caution` #e3b859 · #a87d08 / `--o-caution-text` #eac878 · #846007 / `--o-caution-fill` on `--o-caution-on` #0b0d14 · #14182a): the `pending` badge; the invalid-declaration warning's dashed border (bright) with its heading and code in the `-text` weight; `stale` markers on How.
- **Problem Red** (`--o-problem` #f27878 · #c23c3c / `--o-problem-text` #f79b9b · #ac3232 / `--o-problem-fill` on `--o-problem-on` #0b0d14 · #ffffff): the `lost` and `refused` badges and the `problem` tier badge (fill); error counts, the `N ×` of a nested error group, a category chip's ` · N err`, the problem breakage banner and the rising delta on a cost card (`-text`); the banner border and the error series under a bar spark (bright).
- **Neutral** (`--o-neutral-fill` #6c7491 · #7a829c on `--o-neutral-on` #ffffff · #14182a): in the contract for a status with no role; no badge uses it.

### Chart Ink
Data volume never borrows the accent or semantic hues; it has its own desaturated blue ramp, ordered by contrast against the panel — ink-1 is always the most visible step, so it is the lightest in dark and the darkest in light.
- **Ink 1–4** (#82a9e8 → #2b4468 · #24406e → #b9c4dd): stacked token-chart segments (input / output / cache-create / cache-read), and the heatmap's sequential ramp (ink-4 lowest quartile up to ink-1), an empty day on `--o-border`.
- **Spark Blue** (`--o-spark`, #82a9e8 · #24406e): bar-spark call bars and the trend spark's line; its area under the line at `--o-wash-spark` (0.16 · 0.2).
- **Gapline** (`--o-gapline`, #4c5470 · #ccd2e2): pre-coverage shading on OTEL-fed bar sparks at `--o-wash-precov` (0.22 · 0.35).
- **Axis** (`--o-axis`, #6f7794 · #a0a8be): non-text chart lines only. Axis *text* is `--o-dim`; the dark axis value is 3.99:1 on panel, below AA for text (ticket #47).

### Stage Identity
A categorical palette for How: which declared stage a stage panel or run card belongs to, carried only by a 3px left rule (inline `--stage`, falling back to `--o-stage-off`). Labels stay `--o-text`; no `-text` weight exists.
- **Stage 1–5** (Teal #2fc4c4 · #096060, Violet #a98cf5 · #6137c5, Magenta #e07ad8 · #922a82, Orange #f0995a · #8a4209, Gold #d4c95a · #61570d): positional per declaration, cycling past five; light values hold ≥6.5:1 on the light panel.
- **Stage Off** (`--o-stage-off`, #6f7794 · #525a74): off-script run cards, the unbucketed lane, undeclared stages.

### Neutral
- **Ground** (`--o-bg`, #0b0d14 · #fcfcfe): the page; also the tint of card-table header and group rows and the recess of an open detail row.
- **Panel** (`--o-panel`, #141826 · #f1f3f9): top bar, nav row, cards, stat cards, stage panels, chips, popovers, banners.
- **Border** (`--o-border`, #272e45 · #d9dde9): every border, card-header rule, row rule, and the top bar and nav row's bottom rule.
- **Text** (`--o-text`, #dde2f0 · #14182a): primary text and the current nav item.
- **Dim** (`--o-dim`, #9aa3bd · #4a5169): secondary text — pretitle, description, card subtitles, labels, table heads, deltas, notes, axis text, idle nav items and help `?`.
- **Faint** (`--o-faint`, #6f7794 · #767e98): the quietest tier; shipped only as a run card's hover border. Not for text (3.99 · 3.63:1).

### Named Rules
**The One-Contract Rule.** Both themes live in `design/tokens.css` and nowhere else: dark verbatim in `:root`, light behind `@media (prefers-color-scheme: light)` guarded `:root:not([data-theme="dark"])`, plus `[data-theme="light"]` / `[data-theme="dark"]` pin blocks. A new token lands in all four; the two light blocks stay identical; view code never branches on theme.
**The Token-Only Ink Rule.** Every colour renders via a `var(--o-*)` token. View code contains no colour literals; the only non-token paint is `transparent` on hit-target rects and the idle nav rule. Theme-sensitive opacities go through the wash tokens, never literals.
**The Red-With-Blue Rule.** The ok pole is periwinkle blue, never green; red pairs with blue (Few) — in banners, tier badges and cost-card deltas alike. Nothing in the system is green.
**The Filled-Badge Rule.** Badge text sits in its role's `-on` weight on its `-fill`; everywhere else semantic text uses the `-text` weight and the bright weight marks only.
**The Amber-Caution Rule.** Selection amber never carries text and appears only as a cell or column fill, or the selection rule, in a header visual. Caution appears only as `-text`-weight text, a dashed border, or a filled badge carrying its word — never an unlabelled swatch, never a delta. The same form rule separates `--o-stage-5` from caution on How.
**The Own-Ink Rule.** Chart volume ink comes only from the ink/spark tokens. The one semantic colour permitted in a chart is `--o-problem`, for the error series beneath its bar spark.
**The Stage-Rule Rule.** Stage hues are non-text marks only — left rules — positional per declaration, never chart ink and never a stand-in for a semantic role.

## Typography

**Body Font:** system-ui (with 'Helvetica Neue', sans-serif)
**Data/Label Font:** ui-monospace (with 'SF Mono', Menlo, monospace)

**Character:** Zero-fetch system faces, identical in both themes. The sans carries prose, titles, badges and Tabler's uppercase caps labels; the monospace carries everything that is a datum — values, figures, deltas, chips, table heads over data, axis text — with `tabular-nums` where figures align in columns.

### Hierarchy
- **Stat** (600, 24px `--o-stat-size`, 1.25, mono, tabular-nums): stat-card values only. The largest type on any screen.
- **Page title** (600, 20px, 1.4): the view name in the page header.
- **Card title** (500, 16px): every card header, glyph first.
- **Brand** (600, 15px): the top bar's wordmark. The sunk-cost panel's measured median reuses 15px in mono.
- **Body** (400, 13px, 1.5): default prose, ledger entry text, stage and run names.
- **Data** (400, 12px, mono): numeric cells, code, raw-entry `pre` (1.5 when multi-line), the page description (12px sans) and popover text (12px/1.5 sans) share the size. Verbatim error text steps to 11px/1.5 mono `--o-dim`.
- **Caps** (500, 11px, 0.04em, UPPERCASE, sans, `--o-dim`): stat-card labels, card-table header and group rows. The pretitle is its 10px/600 sibling.
- **Label** (600, 10–11px, mono, 0.05em, UPPERCASE, `--o-dim`): `<th>` heads in where's tables, How's section headings and fact heads (10px), ledger entry section heads (11px).
- **Small mono** (400, 11px): card subtitles and notes are 11px sans `--o-dim`; deltas, counts, chip buttons, the theme toggle, run metadata and error occurrences are 11px mono. Badges are 500 11px/1.6 sans. Chart axis text is 9px mono `--o-dim`.

### Named Rules
**The Mono-Datum Rule.** If it is a number, a label over data, or an identifier in a chip, it is monospace; if it is prose, a title or a badge word, it is the sans. Columns of figures carry tabular figures.

## Layout

A Tabler horizontal shell, centred in a 1320px container with 12px gutters. From the top: a 56px **top bar** (brand left, theme toggle right) and a 56px **nav row** (three glyph-led links, the current one on a 2px accent bottom rule), both on `--o-panel` with a 1px `--o-border` bottom rule; then the **page header** 24px below — a wrapping flex row holding pretitle, title and description on the left and the actions slot on the right (window presets, clear, hide cache reads on What and Where; empty on How), gaps 0.75rem × 1.5rem; then the **page body** 24px below, closing on 2rem. The body opens with breakage banners (1rem apart), then the project chip row with its note (and where's coverage line), then on What and Where the header visual as the first card.

Cards stack with 16px between them. Stat cards sit in a four-column grid at 16px gaps, two columns at ≤720px. Card bodies pad 20px; card-table rows pad 0.75rem 20px with 1.5rem column gaps, full-bleed to the card edge, header and group rows 0.5rem 20px. What's ledger is a three-column card-table (`minmax(0,12rem) 1fr auto`: project · session · counts); an open row's entry indents 40px. Where's league keeps its six-column grid (`minmax(9rem,1fr) 128px 3.5rem 3rem 4.5rem 4.5rem`); nested error groups leave it — plain summaries indented 0.6rem, occurrences a further 1rem, verbatim text wrapping. How is a two-column grid (260px aside of stage panels · 1fr), run card bodies a 200px + 1fr grid; both collapse to one column at ≤760px. Wide charts scroll horizontally inside their card, newest day at the right. Chip rows flex-wrap at 0.35rem.

## Elevation & Depth

Per theme. Dark is a hybrid: tonal layering (panel over ground) plus one resting shadow, `--o-elev`, on cards, stat cards and stage panels alike — Tabler's `0 1px 2px` card shadow was not adopted. Light is flat at rest (`--o-elev: none`): borders over elevation, the indigo panels reading as recessed fields on white. Floating surfaces take `--o-elev-float` in both themes. Depth also runs inward: card-table header rows and open detail rows recess to `--o-bg`. The top bar and nav row draw their bottom rule as a 1px inset in `--o-border` — a rule, not elevation.

Motion is one token, `--o-motion` (200ms ease), shipped on a single transition: a run card's border brightens to `--o-faint` on hover, keeping its stage rule. Nothing lifts on hover.

### Shadow Vocabulary
- **Resting** (`--o-elev`: `0 3px 10px rgba(0, 0, 0, 0.45)` dark · `none` light): cards, stat cards, stage panels. A dashed stage panel drops it.
- **Floating** (`--o-elev-float`: `0 8px 24px rgba(0, 0, 0, 0.45)` dark · `0 8px 24px rgba(18, 18, 23, 0.12)` light): the help popover only.

### Named Rules
**The Two-Shadow Rule.** Exactly two shadow tokens: resting (dark only) and floating (both themes). A surface at rest in light is flat; only something that floats above the page casts a shadow there. No bespoke shadows.

## Shapes

Three radii, strictly assigned and theme-invariant: 8px (`--o-radius-card`) for cards, stat cards and the help popover; 6px (`--o-radius`) for stage panels, filled badges, breakage banners, the dashed warning box and the help button; 2px for chip-sized controls — chip buttons, the theme toggle. Borders are 1px `--o-border`, except the stage rule (3px) and the accent rules (2px nav rule, 2px pressed-stat bar). Native `<details>/<summary>` provides all expansion, marker suppressed. Charts are inline SVG rectangles — bars and 12px heat cells, square-cornered; the trend spark alone is a line, with round caps and joins.

### Named Rules
**The Two-Chassis Rule.** A data section is a card (8px); a stage-identity surface is a stage panel (6px, 3px stage rule). Never swap them; a run card borrows only the stage rule.
**The Dashed-Absence Rule.** A dashed border means present but empty, hidden, or invalid — a declared stage with nothing observed, a revealed hidden project chip, the invalid-declaration warning. Solid borders carry everything that has data.

## Components

### Shell
- **Top bar:** 56px, `--o-panel`, brand in 15px/600 sans left, theme toggle right.
- **Nav row:** 56px, links `/what` `/where` `/how` inside `<header>`, each a 16px glyph (list · chart-pie · route) and the view name, padding 0 0.75rem, gap 0.5rem; idle `--o-dim` with a transparent 2px bottom rule, current `--o-text` on a 2px `--o-accent` rule.
- **Page header:** pretitle (10px/600 uppercase 0.04em `--o-dim`) carrying the coverage datum — "synced through … · N sessions" — then the 20px/600 view title, then a 12px `--o-dim` description; actions slot right, in chip buttons.

### Cards
- **Chassis:** `--o-panel`, 1px `--o-border`, 8px radius, `--o-elev`, 16px vertical margin.
- **Header:** min 65px, padding 0.75rem 20px, ruled below in `--o-border`; a 16px/500 title led by its glyph, an 11px `--o-dim` subtitle beneath (hint, or any coverage-gap sentence), and card-actions pushed right (chip rows, the help `?`).
- **Body:** 20px padding. A **headerless card** (How's runs) is body only.

### Card-Tables
- **Grammar:** a visual grammar over the view's own rows, not an element — What's ledger and Where's league keep their `<details>` rows. Full-bleed to the card edge; a header row and group rows in 11px/500 uppercase 0.04em `--o-dim` on `--o-bg`; rows padded 0.75rem 20px, ruled in `--o-border`, the last row unruled. Where's `<table>`s follow the same geometry with 10px/600 mono `<th>` heads and right-aligned 12px mono tabular numerals; errors `--o-problem-text`, unknowns `--o-dim` em-dashes. An open league row recesses to `--o-bg`.

### Stat Cards
- **Style:** the card chassis at 20px padding, in a four-up grid. Top line: the 11px/500 uppercase label left, the delta right (11px mono). Then the 24px/600 mono value, an 11px `--o-dim` line (awaiting analysis · unrecoverable, `+n unknown`, share of tokens — or a blank), and a 32px trend spark 12px below.
- **Delta:** a rounded percent against the equal-length prior window, `—` when there is no whole prior window, no arrow at 0%. `--o-dim` with an arrow glyph on every card except the cost cards (tokens, errors), where up is `--o-problem-text` and down `--o-ok-text`. Never caution.
- **Radio (What):** the four cards (sessions · actions · decisions · ADRs) are `<button aria-pressed>`; the pressed one keys the heatmap and wears a 2px `--o-accent` bar along its top edge. Nothing else changes.

### Trend Spark
- **Grammar:** a 2px `--o-spark` line over a `--o-spark` area at `--o-wash-spark`, over the selected days in date order, own peak. One segment per contiguous run of days; a lone day is a 4px dot. Days before the first synced day are gaps on every card, and on the three analysis cards so is a day whose sessions are all pending (ADR-0030 §7); elsewhere zero is zero.

### Badges
- **Style:** filled, 6px radius, padding 0 0.4rem, 500 11px/1.6 sans, no wrap; `-on` text on the role's `-fill`. Status badges carry their word before the row text: `pending` caution, `lost` and `refused` problem, `empty` and `trivial` ok. Record badges — project, continuation, subagents, `N ADR`, types and categories on Where — and How's `now` take the ok fill. Breakage tiers: `problem` on the problem fill, `informational` on the ok fill. A project badge ellipsises inside its 12rem column.

### Chip Buttons (project chips, window presets, clear, category chips)
- **Style:** 11px mono `--o-dim` on `--o-panel`, 1px `--o-border`, 2px radius, padding 0.2rem 0.55rem.
- **On state:** text and border to `--o-accent`; background unchanged. A category chip carries ` · N err` in `--o-problem-text` on or off. A revealed hidden project chip is dashed.
- **Theme toggle:** the same treatment in the top bar, reading `theme: system|light|dark`; cycles system → light → dark, pinned in `localStorage` and applied as `data-theme` before first paint.

### Help Popover
- **Trigger:** a bare `?` button — the 16px help-circle glyph in `--o-dim`, `--o-text` on hover and focus, 2px `--o-accent` focus outline, 6px radius — in the card's actions.
- **Popover:** the platform `popover` (open, Esc and click-outside are native); `--o-panel`, 1px `--o-border`, 8px radius, `--o-elev-float`, padding 12px 16px, 12px/1.5 text, max-width min(26rem, 100vw − 32px). Anchored below its trigger (bottom span-left, flipping) where the browser supports anchoring, viewport-centred where not. It carries explanation only; coverage statements stay visible.

### Stage Panels (How)
- **Style:** `--o-panel`, 1px `--o-border`, 6px radius, `--o-elev`, padding 0.9rem 1.1rem, a 3px left rule in the stage hue. Status and each stated-process stage are stage panels (a stage at 0.5rem 0.7rem, name 13px, detail 11px mono `--o-dim`). A stage with nothing observed is dashed and shadowless, its name `--o-dim`.
- **Run cards:** headerless cards with the same 3px stage rule, newest first; the current run wears the `now` badge. Off-script is a titled card (route-slash glyph) with its list collapsed behind `show list`.
- **Warning:** the invalid-declaration box is 1px dashed `--o-caution`, 6px radius, its alert-triangle glyph and heading in `--o-caution-text`.

### Breakage Banner
- **Style:** one per open breakage row, at the top of every page body: 12px on `--o-panel`, 6px radius, padding 0.55rem 0.9rem, a 1px border in the tier's bright weight and text in its `-text` weight, led by the tier badge. Problem red pairs with informational blue.

### Error Groups (Where league detail)
- **Style:** inside an open league row's `--o-bg` detail, one nested `<details>` per exact error line — 12px mono `--o-text` summary with the count `N ×` in 600 `--o-problem-text`; each occurrence an 11px mono `--o-dim` line (session link · day) over a wrapping 11px/1.5 `pre`. Uncaptured errors close the list as a stated count, never dropped.

### Icons
- **Set:** 19 glyphs derived from Tabler Icons 3.48.0 (MIT, credited in `LICENSES/tabler-icons.txt`), paths in `build/assets/icons.js`. Markup carries `data-icon="<name>"` placeholders; the script fills each with a 16px inline SVG, stroke 2, `currentColor`, round caps and joins. One glyph per nav item, card title, help trigger and delta arrow, plus How's clock (Status) and alert-triangle (warning). No webfont, nothing vendored.

### Bar Sparks (signature component)
- **Grammar:** per-day bars on table rows over the shared 30-calendar-day axis ending at the last synced day: 3px bars, 1px gaps, 14px tall, own peak, minimum bar 1px. A missing day is a gap, never a zero-height bar. An error series, when present, is a 6px `--o-problem` band 2px beneath, on its own peak. OTEL-fed sparks shade the pre-coverage region in `--o-gapline` at `--o-wash-precov`.

### Header Visuals
- **Token chart (Where):** the bar grammar scaled up — 14px bars, 3px gaps, 96px tall, stacked ink-1…ink-4; 9px mono `--o-dim` axis labels every 7th day; a selected column washes in `--o-compare` at `--o-wash-sel` with the compare rule beneath at `--o-wash-rule`.
- **Session heatmap (What):** one 12px cell per local day, 2px gaps, seven rows Monday-first (Mon and Fri labelled), one column per week, month labels on top in 9px mono `--o-dim`. Level is `ceil(value / peak × 4)` keyed by the pressed stat card: empty on `--o-border`, then ink-4 → ink-1; in-window cells flip to compare at four opacities.
- **Selection:** a day is a focusable column in either visual (focus is an `--o-accent` stroke); click toggles, shift-click ranges, a preset or clear empties the shared day set.

## Do's and Don'ts

### Do:
- **Do** render every colour via a `var(--o-*)` token; tokens.css is inlined into every page and is the only place a colour value lives.
- **Do** land any new token in all four blocks of tokens.css — dark `:root`, the light media block, and both pin blocks — and keep the two light blocks identical.
- **Do** put a data section in a card (8px, ruled 65px header, 20px body) and stage identity in a stage panel (6px, 3px stage rule).
- **Do** use the `-text` weight for semantic text, the `-fill`/`-on` pair for a filled badge, and the bright weight for marks only.
- **Do** keep any sentence that states a coverage gap or capture start visible under its card title; only explanation goes behind the help `?`.
- **Do** draw absence as absence: missing day = gap, unknown value = `--o-dim` em-dash, unpaired = "+n?", pre-coverage = shaded, trend spark broken across unsynced or unselected days.
- **Do** keep bar sparks on the shared 30-calendar-day axis with their own peak, and figures in monospace with tabular-nums.
- **Do** draw every glyph from `icons.js` as 16px inline SVG in `currentColor`.

### Don't:
- **Don't** branch on theme in view code or assets; views are theme-blind.
- **Don't** introduce green; the ok pole is periwinkle blue and red pairs with blue, in both themes.
- **Don't** put the accent on body text or large surfaces — it marks interaction and current state only.
- **Don't** let selection amber carry text, or caution appear as an unlabelled swatch or a delta hue.
- **Don't** use accent, compare, or semantic hues for chart volume ink; the error series in `--o-problem` is the sole semantic chart mark.
- **Don't** set text in `--o-axis`, `--o-faint`, or a stage hue.
- **Don't** give a surface at rest a shadow in light, or invent a shadow beyond `--o-elev` and `--o-elev-float`.
- **Don't** fetch fonts, load imagery, vendor Tabler, or add dependencies; the surface is system faces, inline SVG and one inline stylesheet.
