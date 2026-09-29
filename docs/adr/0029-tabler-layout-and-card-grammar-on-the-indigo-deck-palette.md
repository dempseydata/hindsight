# ADR-0029: Tabler layout and card grammar on the Indigo deck's palette

**Date:** 2026-09-29 · **Status:** accepted · **Decides:** map [#39](https://github.com/dempseydata/hindsight/issues/39) (Tabler look, decided per strand), closed by [#49](https://github.com/dempseydata/hindsight/issues/49) · **Amends:** ADR-0007 (Look, Spark grammar) · **Untouched:** ADR-0008, ADR-0017

## Context

Tabler (`@tabler/core` 1.6.0, MIT) was weighed against the incumbent V3 · Indigo deck **per strand**: layout and cards first, as information architecture, in a greybox over `local-data/hindsight.db`; palette second, on the winning layouts. Every strand was judged comparatively by the operator, side by side on identical real data, on switchboards served by the real `serve.py` — no pre-set criteria. The lean going in was towards the incumbent. The facts Tabler's look is made of are in [#40](https://github.com/dempseydata/hindsight/issues/40); each strand's full answer is its ticket's resolution comment, cited below.

Tabler is a **reference, not a dependency**: nothing from its dist is vendored (ADR-0008 stands), its look is ported by hand into `design/tokens.css` and `build/assets/`.

## Decision

The outcome is a mix: **Tabler's layout and card grammar, on the Indigo deck's palette.**

1. **Shell** ([#41](https://github.com/dempseydata/hindsight/issues/41)). Tabler horizontal: a 56px top bar (brand left, theme toggle right), a 56px nav row (current view on a 2px bottom rule), then a page header — coverage split into an uppercase pretitle ("synced through … · N sessions") and a description, the view name as a 20px/600 title, window presets / clear / hide cache reads in the actions slot. The page body opens with breakage banners, then the project chips, then the header visual as its first card. `container-xl`, 1320px. The actions slot keeps the incumbent's 11px mono chips ([#42](https://github.com/dempseydata/hindsight/issues/42)).
2. **Card grammar** ([#42](https://github.com/dempseydata/hindsight/issues/42)), seven patterns of eight: cards with a ruled 65px header (16px/500 title), 20px body padding, 8px radius; long notes behind a help `?` popover; controls in card headers as card-actions; tables as full-bleed card-tables (What's ledger included, day headings as tinted group rows); stat cards (11px label, 24px/600 value, delta vs the equal-length prior window, trend spark); filled 6px badges for status marks; the header visual as a card with the hint as its subtitle; inline-SVG icons.
3. **How** ([#44](https://github.com/dempseydata/hindsight/issues/44)) takes the shell and only part of the grammar: the project selector is a page-body chip row and the actions slot stays empty; no help `?`, the explanatory lines stay visible; Status and the stated-process aside stay **stage panels**; runs become headerless cards; `now` is a filled badge; off-script is a card with its list collapsed; the invalid-declaration warning stays a dashed box.
4. **Two chassis, on purpose** ([#46](https://github.com/dempseydata/hindsight/issues/46)). The **card** (8px) holds data; the **stage panel** (6px, 3px stage-hue rule) marks stage identity. Both carry the incumbent's `--o-elev` — the radius is the only difference. Tabler's `0 1px 2px` card shadow is not adopted.
5. **Palette stays incumbent, dark and light as a pair** ([#45](https://github.com/dempseydata/hindsight/issues/45)); ADR-0017's Ledger light theme stands. The grammar adds tokens the deck lacked, with the values judged in #45: a fill + on-fill pair per role — `--o-{ok,caution,problem,neutral}-fill` / `-on`, each AA in both themes — `--o-elev-float` for floating surfaces (the help popover), and `--o-wash-spark` for the trend spark's area. Stat-card deltas: on the token and error cards, up is `--o-problem-text` and down `--o-ok-text`; every other card's delta is `--o-dim`, arrow only. `caution` never appears on a delta.
6. **Two sparks.** ADR-0007's grammar is renamed the **bar spark** and stays as it was, on table rows: per-day bars on the shared 30-calendar-day axis, own peak, pre-coverage shaded. Stat cards carry a **trend spark**: a line plus a `--o-wash-spark` area over the *selected* days in date order, own peak. Zero is drawn as zero — every stat card counts sync-derived data, so a day without usage is a true zero. Under a day-set selection (ADR-0028) the line breaks between non-adjacent days — one segment per contiguous run, a lone day a dot — so no trend is drawn across unselected days. The bar spark on stat cards was on offer in #42 and lost.
7. **Icons** ([#47](https://github.com/dempseydata/hindsight/issues/47)): 16px inline SVG, stroke 2, one glyph per nav item, card title, help and delta, **derived from Tabler Icons 3.48.0** (MIT, © 2020–2026 Paweł Kuna) — some paths verbatim, some simplified. All paths live in one assets module whose header carries the notice; the MIT text sits in one licence file. No webfont.
8. **Selection amber and caution may touch** ([#48](https://github.com/dempseydata/hindsight/issues/48)); no hue moves and `pending` stays caution. The rule: **selection amber never carries text** and appears only as a grid-cell or column fill, or the selection rule, in a header visual. **Caution appears only as text in its `-text` weight, a dashed border, or a filled badge carrying its word**, never as an unlabelled swatch. If either side breaks this, the question reopens. The same form rule covers `--o-stage-5` ≈ caution on How (ΔE 0.047), stage hues being non-text marks only (ADR-0007, #71 amendment).

## Chosen knowing the cost

No density trim was taken ([#46](https://github.com/dempseydata/hindsight/issues/46)); every one was measured and declined. At 1440 × 900: What shows 3 ledger rows above the fold (master 11), its first row at 697px (417); Where's first panel sits at the fold, 869px (434); How's Status moves 165 → 314px and its page grows 15–17% — that cost is the shell's and no trim reaches it. Page heights: What 4468 vs 3883, Where 6354 vs 4700.

## Alternatives rejected

- **Tabler as shipped** (neutral + `#066fd1`) and **Tabler bridged** (slate + `#4263eb`), each with Tabler's raised-white light structure — lost to the incumbent as a pair. The comparison tilted towards the incumbent's type (Tabler `-text` weights held just past AA by rule); stated in #45.
- **The incumbent stacked header**; Tabler's condensed, vertical and overlap shells (dropped before the build); combo (dead on 1.6.0).
- **Tabler's 40px buttons and `nav-segmented`** in the actions slot.
- **Bar spark on stat cards**; a spark only where the trend is the point (recovers nothing on Where's two rows of four).
- **`card-sm`, tighter padding, 49px card headers, `.5rem` rows, radius 6 everywhere** — every density trim.
- **`card-status-start`** for stage identity; stat cards for How's Status (they would count the model's bullets).
- **Hand-drawn glyphs** — the prototype's were Tabler paths all along; redrawing ~20 buys nothing.

## Consequences

- One spec via `to-spec`: token values, the shell, the card grammar for all three views and the shared chrome, the glyph path table, attribution. The restyle is a separate build effort.
- The amber/caution rule joins the floor rules in `tokens.css`'s header comment, beside the rules ADR-0007 already puts there.
- `syncCtl()` in `build/assets/chrome.js` finds the How link by `a[href^="/how"]`; a restyle that touches the nav must keep that href relative or find the link another way (#45, #46).
- `DESIGN.md` and its sidecar are re-derived and screenshots retaken after the build (ADR-0007 addendum).
- Fold measurements must open each view in a fresh browser context: the filter state carries across views (issue #10) and skews the next view.
- Vocabulary — card, stage panel, header visual, stat card, bar spark, trend spark — recorded in `CONTEXT.md` under "Served UI"; Tabler's own component names (page header, card-table, badge …) stay in the spec.
