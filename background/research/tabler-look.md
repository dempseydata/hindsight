# Tabler 1.6.0's look — layouts, card grammar, palette, and the gap to Hindsight

**Ticket:** [#40](https://github.com/dempseydata/hindsight/issues/40), part of map [#39](https://github.com/dempseydata/hindsight/issues/39) · **Date:** 2026-09-26 · **Method:** `npm pack @tabler/core@1.6.0` into a scratch directory (nothing vendored), read `dist/css/tabler.css`, `dist/css/tabler-themes.css` and the shipped `scss/`; Tabler's GitHub repo at the release tag `@tabler/core@1.6.0` (released 2026-09-25) for the preview layouts (`shared/layouts/DefaultLayout.astro`, `shared/components/navbar/Navbar.astro`, `shared/components/layout/PageHeader.astro`, `preview/pages/layout-*.astro`), and tag `v1.2.0` for the two layouts 1.6.0 no longer ships. Vertical offsets were computed from the CSS and then **measured**: a throwaway harness page per layout (the `DefaultLayout` skeleton over the 1.6.0 dist CSS) opened in Chromium at 1440 × 900 and 900 × 900, `getBoundingClientRect()` on the first card. Hindsight's side was read from `design/tokens.css`, `build/assets/*.css`, `build/assets/where.html`, `render()` in `build/serve.py`, and measured the same way on the running views server (pixel offsets only; nothing from the page's content is recorded). Contrast ratios are WCAG 2.x, computed from Tabler's OKLCH values by an OKLCH → sRGB conversion whose output matches the hex Tabler writes in its own scss comments.

Citations: `tabler.css:N` is a line of the unminified dist file; `_variables.scss:N` is `scss/_variables.scss` in the package. Values are quoted, never files.

Facts only. What to adopt is the prototypes' job.

---

## 1. Page layouts

### The shell, as 1.6.0 renders it

`DefaultLayout.astro` emits one skeleton for every app page and **always renders both navigations**; which one shows is decided by `data-bs-*` attributes on `<html>`, so the theme panel can switch layout at runtime:

```
div.page                                   flex column, min-height 100%        tabler.css:16241
├─ aside.navbar.navbar-vertical.navbar-expand-lg   (sidebar, 16rem)
├─ header.navbar.navbar-expand-md          top bar: brand, user/theme/apps side group
├─ div.navbar-expand-md > .navbar          menu row (omitted when condensed: the menu moves into the top bar)
└─ div.page-wrapper                        flex column, flex 1
   ├─ div.page-header > .container-xl > .row.g-2.align-items-center
   │     .col: .page-pretitle / h2.page-title / optional .text-secondary description
   │     .col-auto.ms-auto: header actions slot (buttons)
   ├─ main.page-body > .container-xl > .row.row-deck.row-cards > .col-* > .card
   └─ footer
```

Driving values (all rem, root 16px):

| Piece | Value | Source |
| --- | --- | --- |
| `.navbar` | `min-height: 3.5rem`, padding `0.25rem 0`; bottom rule is `box-shadow: inset 0 -1px 0 0 var(--tblr-navbar-border-color)`, not a border | `tabler.css:4116`, `:13787` |
| `.navbar .navbar-nav` | `min-height: 3rem` | `tabler.css:13815` |
| `.page-wrapper .page-header` | `margin: var(--tblr-page-padding-y) 0 0`; `.page-header` `min-height: 2.25rem` | `tabler.css:16300–16309` |
| `.page-pretitle` | 0.75rem / 1rem, weight 500, uppercase, 0.04em, `--tblr-secondary` | `tabler.css:16319` |
| `.page-title` | `--tblr-font-size-h2` 1.25rem / `--tblr-line-height-h2` 1.75rem, weight 600 | `tabler.css:16328`, `:13471` |
| `.page-body` | `margin-top` and `margin-bottom: var(--tblr-page-padding-y)` | `tabler.css:16268` |
| `--tblr-page-padding-y` | `var(--tblr-spacer-4)` = 1.5rem | `tabler.css:13603` |
| `--tblr-page-padding` | 1rem; `0.5rem` below 992px | `tabler.css:13602`, `:13612` |
| `.container-*` gutter | `calc(var(--tblr-page-padding) * 2)` → 1rem each side (0.5rem below 992px) | `tabler.css:673` |
| `.container-xl` max-width | 1140px ≥1200px, 1320px ≥1400px | `tabler.css:698–707` |
| `.row-cards` | `--tblr-gutter-x` and `--tblr-gutter-y: var(--tblr-page-padding)`; the row's `margin-top: -gutter-y` and each col's `margin-top: +gutter-y` cancel on the first row | `tabler.css:19639`, `:716–731` |
| Header action button | `--tblr-btn-input-min-height` = 1.25rem + 2 × 0.5625rem + 2 × 1px = **40px** | `tabler.css:13521` |
| `--tblr-sidebar-width` | 16rem (folded 4rem) | `tabler.css:13604` |

### Vertical space before the first card

Common tail: `.page-header` top margin 24 + header row 44 (pretitle 16 + title 28 = 44, which beats the 36px min-height and the 40px button) + `.page-body` top margin 24 = **92px** below whatever navigation sits above the wrapper.

| Layout | How 1.6.0 gets it | Arithmetic | Computed | Measured (1440 wide) |
| --- | --- | --- | ---: | ---: |
| **Horizontal** (default, `index`, `layout-horizontal`) | two-row navbar: top bar + menu row | 56 + 56 + 92 | 204 | 204 |
| **Condensed** (`navbarCondensed`) | menu folded into the single top bar | 56 + 92 | 148 | 148 |
| **Vertical** (`navbarPosition="vertical"` → `data-bs-navbar-position=vertical`) | ≥992px: fixed 16rem sidebar, `.page-wrapper` `margin-inline-start: calc(var(--sidebar-width) + gap)`; both horizontal navbars `display: none` (`tabler.css:14998`) | 0 + 92 | 92 | 92 (wrapper starts at x = 256) |
| **Fluid** (`layout="fluid"` → `data-bs-layout=fluid`) | horizontal, every `.container*` `max-width: 100%` (`tabler.css:13739`) | 56 + 56 + 92 | 204 | 204 (card at x = 16, not 76) |
| **Boxed** (`layout="boxed"`) | ≥768px: body `padding: 1rem`, `.page` `max-width: 1320px`, 1px border, 6px radius, backdrop `oklch(26.86% 0 0)` + white 10% gradient (`tabler.css:13748–13775`) | 16 + 1 + 204 | 221 | 221 |
| **Navbar floating** (new in 1.6; `layout-navbar-floating` = condensed + floating) | navbar gets `--navbar-margin: 0.5rem` on all sides, 8px radius, outline instead of rule (`_navbar.scss` "Navbar floating") | 8 + 56 + 8 + 92 | 164 | not measured |
| **Navbar overlap** | *not a 1.6.0 preview page.* `v1.2.0` recipe: condensed + dark + `.navbar-overlap`. The class still ships: `::after` band `height: 9rem`, `top: 100%`, `background: inherit` (`tabler.css:16133`) | 56 + 92 | 148 | 148 |
| **Combo** | *not a 1.6.0 preview page.* `v1.2.0` recipe: dark sidebar + condensed top bar without brand or menu, `d-none d-lg-flex` | 56 + 92 beside the sidebar | 148 | **not reproducible** — see below |

- **Overlap geometry:** the 144px band runs from y = 56 to y = 200, so the page header (y 80–124) and the top 52px of the first card row (from y = 148) sit on the navbar's colour.
- **Combo is not reachable on 1.6.0 CSS as shipped.** With no position attribute and a horizontal navbar as a direct child of `.page`, `html:not([data-bs-navbar-position=vertical]) .page:has(> [class*=navbar-expand]:not(.navbar-vertical)) > .navbar-vertical { display: none }` hides the sidebar (`tabler.css:14989`); with the attribute set, `tabler.css:14998` hides the top bar instead. Measured: the sidebar computed `display: none`, first card at 148. `DefaultLayout.astro` at the tag has no `navbarOverlap` or combo prop, although the repo's own `.agents/skills/page-layouts/SKILL.md` still lists `navbarOverlap` (stale doc).
- **Other 1.6.0 layout pages** not in the ticket's list: `layout-folded` / `layout-folded-hover` (4rem icon rail), `layout-vertical-right`, `layout-vertical-transparent`, `layout-vertical-floating`, `layout-fluid-vertical`, `layout-navbar-sticky`, `layout-navbar-dark`, `layout-rtl`.

### At 13px body text

Tabler's body is `--tblr-body-font-size: 0.875rem` (14px) with `--tblr-body-line-height: 1.4285714286` (20px) (`tabler.css:100–102`; `_variables.scss:402`, `:438` defines line-height as `1.25rem / font-size-base`). **Every shell dimension above is rem, not em**, so setting 13px body text moves none of them. Measured: with `:root { --tblr-body-font-size: 13px }` the first card stays at y = 204 in the horizontal layout; only body-text lines inside the card shrink (first card 189px → 186.1px tall). What does scale with body size is whatever is sized in `em` — chiefly `.badge` (0.85714285em, `tabler.css:17126`). Below 992px the vertical offsets are also unchanged (measured 204 / 148 at 900 wide): only `--tblr-page-padding` halves, which moves horizontal gutters, not `--tblr-page-padding-y`.

---

## 2. Card grammar

All from the dist CSS; Bootstrap's base `.card` block (`tabler.css:4565`) is overlaid by Tabler's (`tabler.css:18497`).

| Element | Padding / size | Type | Surface, border, shadow | Source |
| --- | --- | --- | --- | --- |
| `.card` | — | inherits body (14px / 20px) | bg `--tblr-bg-surface` (white light / `gray-800` dark); `1px solid --tblr-border-color-translucent`; radius `--tblr-border-radius-lg` **8px**; `box-shadow: var(--tblr-shadow-card)` = `0 1px 2px 0` shadow-colour at 12.5%. Nested `.card .card` drops the shadow; `a.card:hover` lifts to `--tblr-shadow-card-hover` (`0 4px 6px -2px` + `0 10px 15px -3px`) | `tabler.css:4565–4596`, `:13499`, `:18520` |
| `.card-header` | `1.25rem 1.25rem` (20px) | — | `display: flex; align-items: center`; bg transparent (`--tblr-card-header-bg: transparent`); `border-bottom: 1px` translucent | `tabler.css:4649`, `:18691` |
| `.card-title` | margin-bottom 1rem (0 inside a header) | **1rem, weight 500**, line-height 1.5rem, `--tblr-heading-color` (`gray-900` light, inherit dark) | — | `tabler.css:18788–18803` |
| `.card-subtitle` | margin-bottom 1.25rem; inside a title: `margin-inline: 0.25rem 0` | weight 400, `--tblr-secondary`; 0.875rem when inside `.card-title` | — | `tabler.css:18806–18819` |
| `.card-actions` | `margin-block: -0.5rem`, `margin-inline: auto -0.5rem`, `padding-inline-start: 0.5rem` — pushed right, bleeds into the header padding | — | — | `tabler.css:18681` |
| `.card-body` | `1.25rem` (20px); `.card-sm` 1rem; `.card-md` 2.5rem ≥768; `.card-lg` 2rem / 4rem ≥992 | — | stacked bodies separated by `border-top: 1px` | `tabler.css:4621`, `:18821–18856` |
| `.card-footer` | `1.25rem` | — | bg `--tblr-card-cap-bg` = `--tblr-bg-surface-tertiary` (`gray-50` light / `gray-800` dark); `border-top: 1px` translucent; `margin-top: auto` | `tabler.css:4661`, `:18750` |
| Header height (title only) | 20 + 24 + 20 + 1 = **65px** | | | computed |
| **Stat card** (demo `cards/charts/Sales.astro`) | a plain `.card-body` (20px) | `.subheader` 0.75rem / 1rem, 500, uppercase, 0.04em, secondary — **label above**; value `.h1` **1.5rem / 2rem, weight 600**, `mb-3`; trend via `Trending.astro`: `text-green` + arrow-up when > 0, `text-red` + arrow-down when < 0, `text-muted` at 0 | — | `tabler.css:24222`, `:24021`, `:199–205` |
| `.card-table` | cells `0.75rem`; first/last cell `padding-inline` 1.25rem to align with the card padding; no outer cell borders | `thead th`: **0.75rem / 1rem, 500, uppercase, 0.04em**, `padding-block: 0.5rem`, bg `--tblr-bg-surface-tertiary` | row rules `--tblr-border-color-translucent` | `tabler.css:2268–2294`, `:18913–18960`, `:23330` |
| `.status-dot` | 0.5rem circle, pill radius | — | fill `--tblr-status-color` | `tabler.css:22956` |
| `.status` | height 1.5rem, padding `0.25rem 0.75rem`, gap 0.5rem | 0.875rem, 500, line-height 1 | text = the raw colour; bg = colour at 10% (`color-mix`); pill radius | `tabler.css:22774` |
| `.badge` | `0.25em 0.5em` | **0.85714285em** (12px at 14px body), 500, line-height 1, letter-spacing 0.04em | bg `--tblr-bg-surface-secondary`, text `--tblr-secondary`, 1px transparent border, radius `--tblr-border-radius` **6px**; `.badge-outline` and `.bg-*-lt` (colour text on 10% tint) variants | `tabler.css:17123–17184`, `:25239` |
| `.empty` | `1rem`; `3rem` ≥768; centred column | `.empty-title` 1.25rem / 1.75rem, 600; `.empty-header` 4rem, weight 300, secondary; icon 3rem, secondary | `.empty-bordered`: 1px border, 6px radius | `tabler.css:19465–19532` |

**Borders versus shadows.** A Tabler card uses both: a translucent 1px border (light: `gray-800` at 11.9%; dark: `rgba(128, 150, 172, 0.2)`, `tabler.css:137`) plus a 1–2px shadow. `--tblr-shadow-color` is `light-dark(rgba(18, 18, 23, 0.4), #000)` (`tabler.css:13487`), so the card shadow resolves to ~5% black in light and 12.5% black in dark (the scss comment at `_variables.scss:925–933` says the light branch is pre-scaled by 0.4 on purpose). Radius scale: xs 2px, sm 4px, default 6px, lg 8px (cards), xl 1rem, all multiplied by `--tblr-border-radius-scale` (`tabler.css:13503–13512`), which the themes file sets to 0 / 0.5 / 1 / 1.5 / 2.

---

## 3. Palette

### How theming is wired

- **Dark mode** is `color-scheme: dark` on `[data-bs-theme=dark]` / `[data-theme=dark]` (`tabler.css:16469`), and every surface token is a `light-dark()` pair (`tabler.css:13563–13606`). The dist CSS contains **no `prefers-color-scheme` query** (0 occurrences); following the OS is left to Tabler's JS setting the attribute.
- **Theme base** (`tabler-themes.css`, `[data-bs-theme-base=…]`) swaps only the eleven `--tblr-gray-50…950` steps. It sets **no separate dark values**: dark mode picks different steps of the same scale.
- **Primary** (`[data-bs-theme-primary=…]`) swaps only `--tblr-primary`. The same file also carries radius-scale and font options (`monospace` sets body to 80%), and an `inverted` primary (`gray-800` light / `#fafafa` dark).
- **Semantic colours are theme-invariant** — one value each, declared once (`tabler.css:51–56`, `:13256–13284`), not redefined under the dark selectors.

### Theme bases — the steps a UI actually uses

Role mapping (`tabler.css:13563–13606`): light page `--tblr-body-bg` = `--tblr-bg-surface-secondary` = `gray-50`; light card `--tblr-bg-surface` = `#fff`; light body text `gray-700`; light secondary text `gray-500`; light border `gray-200`. Dark page `gray-900`; dark card `gray-800`; dark body text `gray-200`; dark secondary `gray-400`; dark border `gray-700`. Hex values are Tabler's own comments in `scss/tabler-themes.scss` (neutral: `_variables.scss:38–48`); they are the Tailwind v3 grey families.

| Base | gray-50 (light page) | gray-200 | gray-500 | gray-700 | gray-800 (dark card) | gray-900 (dark page) | Body text on card, light / dark | Secondary on card, light / dark |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| **neutral** (default, `oklch(… 0 0)`) | `#fafafa` | `#e5e5e5` | `#737373` | `#404040` | `#262626` | `#171717` | 10.37 / 12.01 | 4.74 / 6.00 |
| **slate** | `#f8fafc` | `#e2e8f0` | `#64748b` | `#334155` | `#1e293b` | `#0f172a` | 10.35 / 11.87 | 4.76 / 5.71 |
| **gray** | `#f9fafb` | `#e5e7eb` | `#6b7280` | `#374151` | `#1f2937` | `#111827` | 10.31 / 11.86 | 4.83 / 5.78 |
| **zinc** | `#fafafa` | `#e4e4e7` | `#71717a` | `#3f3f46` | `#27272a` | `#18181b` | 10.44 / 11.74 | 4.83 / 5.81 |

Also shipped: `stone` (warm, `#1c1917` dark page) and `pink` (an easter egg per the scss comment, not in the settings panel). Chroma is tiny throughout (slate peaks at C ≈ 0.04, hue ≈ 257°); neutral is exactly achromatic. The default is **neutral**, not slate.

### Primary options

Twelve, all `oklch()` in `tabler-themes.css`; hex from `_variables.scss:67–78`. "On primary" is `--tblr-primary-fg` (light `#fafafa`) on the colour, i.e. button text; "link, dark" is the dark-mode link colour `color-mix(in oklab, white 40%, primary)` on a neutral `gray-800` card.

| Primary | Hex | On primary | On white | Link, dark |
| --- | --- | ---: | ---: | ---: |
| blue (default) | `#066fd1` | 4.79 | 5.00 | 6.29 |
| azure | `#4299e1` | 2.93 | 3.05 | 8.09 |
| indigo | `#4263eb` | 4.77 | 4.98 | 6.33 |
| purple | `#ae3ec9` | 4.64 | 4.85 | 6.37 |
| pink | `#d6336c` | 4.42 | 4.62 | 6.50 |
| red | `#d63939` | 4.47 | 4.66 | 6.48 |
| orange | `#f76707` | 2.92 | 3.04 | 8.07 |
| yellow | `#f59f00` | 2.04 | 2.13 | 9.83 |
| lime | `#74b816` | 2.34 | 2.44 | 9.13 |
| green | `#2fb344` | 2.63 | 2.74 | 8.56 |
| teal | `#0ca678` | 2.99 | 3.12 | 7.99 |
| cyan | `#17a2b8` | 2.92 | 3.05 | 8.09 |

Only blue, indigo, purple (and nearly pink/red) put light button text at or near AA 4.5:1. Light-mode links are the raw primary (`--tblr-link-color: light-dark(var(--tblr-primary), …)`, `tabler.css:13579`).

### The semantic set

`$success: $green`, `$info: $azure`, `$warning: $yellow`, `$danger: $red` (`_variables.scss:586–589`). Each gets `-lt` (10% tint), `-fg` (light text on it), `-darken` (L − 0.06), and `-text-emphasis` / `-bg-subtle` / `-border-subtle` (`tabler.css:72–95`, `:13266–13284`). Contrast on the neutral base:

| Role | Hex | Raw on white card | Raw on dark card (`gray-800`) | `-text-emphasis` light (60% black mix) on white | `-text-emphasis` dark (40% white mix) on `gray-800` |
| --- | --- | ---: | ---: | ---: | ---: |
| success (green, h 145°) | `#2fb344` | **2.74** | 5.52 | 14.73 | 8.56 |
| info (azure, h 247°) | `#4299e1` | **3.05** | 4.95 | 15.26 | 8.09 |
| warning (yellow, h 71°) | `#f59f00` | **2.13** | 7.09 | 13.41 | 9.83 |
| danger (red, h 26°) | `#d63939` | 4.66 | **3.25** | 17.15 | 6.48 |
| primary (blue) | `#066fd1` | 5.00 | **3.03** | 17.43 | 6.29 |

The AA-passing weights exist (`-text-emphasis`), but the colour-as-text components use the **raw** hue: `.text-success` / `.text-danger` (`tabler.css:26053`, `:26080`), `.status-*` text, `.bg-*-lt` badge text (`tabler.css:25239`, `:25359`). Bold figures fail 4.5:1 as rendered text.

### Where it breaks the floor ("semantic red pairs with blue, never green")

1. **The semantic pair itself is red/green**: `success` = green, `danger` = red. Blue exists only as `info` (azure) and `primary`.
2. **Trend indicators** (`shared/ui/Trending.astro`): up = `text-green`, down = `text-red` — the stat card's delta is a red/green pair by construction.
3. **Form validation**: `--tblr-form-valid-color` green, `--tblr-form-invalid-color` red, with 40%-white-mixed variants in dark (`tabler.css:138–141`).
4. **Tabler sparkline**: `--sparkline-negative: var(--red)` against a `currentColor` stroke (`_variables.scss:2244–2245`) — red is paired with whatever the text colour is, not green, so this one does not break the rule by itself.

Adjacent floor points, stated as facts: semantic hues do not change between themes (the floor's `-text` weight is Tabler's `-text-emphasis`, not what the `.text-*` utilities use); `data-bs-navbar-theme=primary` paints the whole navbar in the primary (`_navbar.scss` "Navbar primary"), i.e. the accent on a large surface; Tabler has **no separate chart data-ink palette** — its sparkline inks `currentColor`.

---

## 4. Gap map against Hindsight

### Hindsight today (for scale)

- **Shell** (`chrome.css`, `render()` in `serve.py`): no app bar. `body { max-width: 1280px; padding: 1.1rem 1.4rem 2rem; font: 13px/1.5 var(--o-font) }` on a 16px root. `<header>` holds, in flow: inline `h1` "hindsight" (15px, 600) + inline `nav` (13px links, dim; current = accent + 1px accent underline) + floated theme button; `.cov` coverage line (12px dim); project chips; a note; the `#ctl` row (window presets 7/14/28/90/all, clear, hide-cache-reads, hint); `#chart` (the per-view header visual, ADR-0028). Then the breakage banner(s), then `main` (`margin-top: 1.1rem`). The how view's header stops after `.cov`.
- **Measured first-content offsets** (1440 wide, live data, pixels only): where — first tile **344px**, first panel **434px**; what — first tile **309px**, first ledger row **417px**; how — first panel **184px**. Where's `#chart` alone is 125px tall (starts at 168.5). Hindsight's header carries the filter and the header visual, which Tabler's page header does not, so these are not like-for-like with §1's 92–221px.
- **Panel** `.panel`: padding `.9rem 1.1rem` (14.4 / 17.6px), `1px solid --o-border`, radius `--o-radius` **6px**, `box-shadow: --o-elev` (`0 3px 10px rgba(0,0,0,.45)` dark, `none` light), `h2` 13px bold inside the body, notes 11px dim; where panels lift 1px on hover.
- **Tile** `.tile`: padding `.55rem 1rem .5rem`, min-width 7rem, value **above** label: `600 28px/1.25` mono tabular (`--o-stat-size`), label 11px dim; on what, tiles are a radio group (`aria-pressed`) that keys the heatmap.
- **Tables** (`where.css`): `th` 600 10px mono, uppercase, 0.05em, padding `.25rem .5rem`, no fill; `td` 12px, padding `.3rem .5rem`; numerics mono tabular, right-aligned. The consumer league is a CSS grid of `details/summary` rows, not a table.
- **Small marks**: chips and controls 11px mono, radius 2px, 1px border; `.pchip` 10px mono; `.adr` / `.now` accent-outlined 2px-radius tags; how's stage identity is a 3px left rule.
- **Ground**: dark `--o-bg #0b0d14`, `--o-panel #141826`, `--o-border #272e45`; light `#fcfcfe` ground with **recessed** `#f1f3f9` panels and borders over elevation (ADR-0017). Tabler's light mode is the inverse value structure: grey `gray-50` page with **raised** white cards plus shadow. In dark both put a lighter card on a darker page.

### What maps

| Tabler | Hindsight counterpart | Differences, value for value |
| --- | --- | --- |
| `.card` | `.panel` | radius 8 vs 6px; padding 20 vs 14.4/17.6px; shadow `0 1px 2px` ~12.5% black (dark) vs `0 3px 10px` 45% black (dark), none in Hindsight light; border translucent vs solid token |
| `.card-header` + `.card-title` + `.card-actions` | `.panel h2` + `.panel .note` | Tabler: separate 65px header band, 16px/500 title, ruled off, actions right. Hindsight: 13px bold title inside the body, no rule, no actions slot (panel-scoped controls such as `#cats` sit in the body) |
| `.card-footer` | — | none |
| Stat card (`.subheader` / `.h1` / trend) | `.tile` | label above value (Tabler) vs value above label; 24px/600 system face vs 28px/600 mono; Tabler trend is red/green text, Hindsight tiles carry no trend |
| `.card-table` | `#where table` | header 12px/500/0.04em on a tinted row vs 10px mono/600/0.05em unfilled; cell padding 12px vs ~4.8/8px — Tabler rows are roughly twice as tall |
| `.badge` | `.pchip`, `.adr`, `.now`, chip buttons | 6px radius, filled `bg-surface-secondary`, em-sized vs 2px radius, outlined, fixed 10–11px mono |
| `.status-dot` / `.status` | stage left-rule (how), `.breakage` tier colour | no dot or pill-status component in Hindsight |
| `.empty` | inline `.note` ("no usage yet — run an analysis first") | no empty-state component |
| `.nav-segmented` | `#ctl` window presets | exists in Tabler (`scss/ui/_segmented.scss`); not measured here |
| `.page-header` (pretitle / title / actions) | `.cov` line under the `h1` | no per-view title block; the view name is in the nav and `<title>` only |
| Two-row / condensed navbar | inline `h1` + `nav` | no bar surface, no 56px band, no container |
| `.container-xl` (1140 / 1320px) | `body { max-width: 1280px }` | Hindsight has one fixed measure, no fluid/boxed variants |
| Theme: attribute + `light-dark()`, JS follows the OS | media query + `[data-theme]` pin, three-state (ADR-0017) | Tabler's dist has no `prefers-color-scheme` rule |
| `.breakage` banner | Tabler `.alert` | exists; not catalogued in this ticket |

### What has no Tabler counterpart

- **The what view's calendar heatmap** (the ticket's "year heatmap"; `what.js` `renderHeat`): one 12px cell (2px gap) per local day across the data range, Monday at top, a column per calendar week, four-step ink ramp, cells are focusable buttons carrying the selection. The dist CSS has **no heatmap** (0 occurrences). The nearest shipped pieces are `.tracking` / `.tracking-squares` (a *single row* of blocks: `height 1.5rem`, gap `0.125rem`, min-width `0.25rem`, fill `--tblr-border-color`; `scss/ui/_tracking.scss`) and ApexCharts' heatmap, which map #39 rules out on licence.
- **Bar sparklines on a shared 30-day axis** (`where.js` `sparkSvg`): every spark spans the same 30 calendar days ending on the last data day, 3px bars / 1px gap / 14px high, own peak per spark, an optional 6px error lane beneath, pre-coverage days shaded (`--o-gapline` at `--o-wash-precov`), per-day tooltips. Tabler 1.6.0 **does** ship a sparkline (`js/src/sparkline.ts`, types `line | bar | circle | tristate`, default 80 × 24, `min`/`max` forceable, `barGap` 2, `barRadius` 2, CSS sizes in `_variables.scss:2242–2256`), but it takes a bare value array: no date model, so a shared calendar axis, the distinction between a gap and a zero, the pre-coverage shading and the error lane would all be the caller's job.
- **Day-set selection** (ADR-0028): click days on the header visual to build a set, shift-click for a range, shared across what ↔ where. Tabler's selection primitive is a popup form control — `js/src/datepicker.ts` over vanilla-calendar-pro with `selectionMode` `single | multiple | multiple-ranged` — not selection on the data visual itself.
- **The header token chart** (where): stacked per-day bars (14px bar, 3px gap, 96px high, 16px axis) inked `--o-ink-1…4`. Tabler's charts are ApexCharts (`libs.json`), out of scope.
- **Stage identity hues, washes, and a chart-ink palette separate from semantic and brand** — Tabler has one colour family serving primary, semantic and data roles.

---

## Not verified

- The measured offsets come from a harness rebuilt from `DefaultLayout`'s markup with simplified navbar content (brand, one link, an avatar), not from Tabler's built preview site; real navbar content could only exceed the 3.5rem min-height if it were taller than 3rem. Navbar-floating (164px) is computed, not measured.
- Overlap and combo are `v1.2.0` recipes applied to 1.6.0 CSS; whether Tabler intends combo to be dead in 1.6.0 or reachable some other way was not established.
- Contrast ratios for `color-mix()` results (`-text-emphasis`, dark links) are my oklab mixes; browsers can differ in the last decimal. Base hues match Tabler's own hex comments exactly.
- Tabler's documentation site was not consulted; the ApexCharts demo cards' colour choices were not examined; `.alert` and `.nav-segmented` were not measured.
- Hindsight's measured offsets depend on live data (chip count, chart height, wrapping of the coverage line) and on the viewport; they are indicative, not constants.
