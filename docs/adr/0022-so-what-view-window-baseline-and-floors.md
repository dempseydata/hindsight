# ADR-0022: The so-what view reads the shared header window, states two baselines side by side, and floors sparsity before magnitude

**Date:** 2026-09-11 · **Status:** accepted · **Decides:** [issue #20](https://github.com/dempseydata/hindsight/issues/20); map [#18](https://github.com/dempseydata/hindsight/issues/18) · **Touches:** ADR-0021, ADR-0014, ADR-0010

## Context

A pattern (ADR-0021) is a cross-session fact stated against the project's own baseline, and *nothing to report* was named before the window, the baseline or the floor that decide it were. The Stage A prototype ([#19](https://github.com/dempseydata/hindsight/issues/19)) ran a fixed 14-day window and found three things that bear on the definition: a 14-day preceding baseline is thin more often than not on this machine while all prior history always exists once a project clears a few days; the preceding and the history baseline can disagree materially on the same window (hindsight-old's work per day: +12% mean / +56% median against the preceding fortnight, +111% / +153% against history); and mean and median disagree in sign on modest cost moves because daily work tokens swing tenfold inside one project.

Sessions and active days come apart too: hindsight-new's fortnight holds 4 active days and 16 sessions, career-ops's last week 4 sessions over 4 days. A floor in days alone would call the densest project thin; a floor in sessions alone would let a per-day median over two days through unflagged.

## Decision

- **Window: the shared header window.** The view reads the what/where filter state as those views do — presets 7/14/28/90/all, default 14, anchored to the last-synced day, bar-click ranges included — and adds no time chrome of its own. It is the where-view's sibling, not the how-view's. The consequence is exported to compute placement ([#25](https://github.com/dempseydata/hindsight/issues/25)): Stage A is computed at render time or cached per window, and Stage B, if built, fixes its own window, since a stored artefact cannot follow an arbitrary selection.
- **Baseline: both, side by side.** Every pattern carries a *preceding* baseline (the window of equal length ending where this one starts) and a *history* baseline (everything before the window), each present only when it clears the sparsity floor and otherwise stated as *no baseline*. One definition for every signal; the baseline is a property of the pattern, not the signal. The two can disagree, and showing both is the juxtaposition rule (ADR-0010) doing its job rather than the view picking a winner.
- **Sparsity floor, then magnitude floor.** The sparsity floor — at least 3 sessions with usage and at least 3 active days — applies identically to the window and to each baseline. The window has three states: **too thin** (below the floor, empty included — a coverage statement under the coverage-window rule, stating what was seen and stopping), **nothing to report** (clears the floor; no row clears its magnitude floor — a result, and the empty case Stage B's eval set must hold), and **patterns**. A signal whose input does not exist — drift with no valid declaration — reads **absent**, a fact about the project rather than the window.
- **Magnitude floors gate the row, per signal, and median gates the trend.** A pattern exists only when at least one of its rows clears its floor; rows below it are dropped, never listed. Consumer: calls ≥ 10 and either error share ≥ 0.10 or token share ≥ 0.25, with the reason carried on the row. Cost trend: |median work-per-day lift| ≥ 0.30 against a present baseline, mean stated beside it and never gating. Drift: a newly off-script name or newly off-script top-level write path at ≥ 3 in the window, with the off-script share always stated on the pattern as the rows' context. The values are calibration knobs to be set at the greybox ([#28](https://github.com/dempseydata/hindsight/issues/28)) over real data; the shape is what this ADR decides.

## Considered options

- **A fixed 14-day span.** Every pattern precomputable and storable, and Stage A and B share a window for free — at the price of a view that ignores the header selection sitting above it, a second time model for the operator to hold.
- **Header presets only, bar-click ranges inert.** Five cacheable windows, but part of the shared chrome would do nothing on one view.
- **One baseline with fallback** (preceding when it clears the floor, else history). One comparison per row, but the kind flips as a project ages and the disagreement the prototype showed is real disappears.
- **History only.** Never thin, never "versus last fortnight".
- **Five active days as the floor** (the prototype's provisional value). Fails hindsight-new at 14 days and every project at 7 days in the charting week — the floor reporting on the preset, not the data.
- **Pattern-gated magnitude** (all rows shown once any clears). Reintroduces the wall of rows v1 emitted and the prototype cut.
- **Mean as the trend gate.** Swung by single heavy days.

## Consequences

- CONTEXT.md gains *window*, *baseline*, *sparsity floor*, *magnitude floor*, *too thin* and *absent*; *nothing to report* is narrowed to the cleared-floor case.
- Stage A must be cheap enough for render time or cached per window — the measured query cost decides which in #25.
- Stage B's eval set, if Stage B is built, holds too-thin and nothing-to-report windows as distinct cases.
- The greybox calibrates the knob values on real data; changing a value is a tokens-style edit in one place, not a redesign.
