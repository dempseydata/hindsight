# ADR-0004: The audit format — session granularity, cross-project store, mechanical ADR counts

**Date:** 2026-08-16 · **Status:** accepted · **Decides:** [Lock the audit format](../../background/tickets/014-lock-the-audit-format.md), on the evidence of the [what-view greybox](../../background/tickets/005-greybox-the-what-view-audit-log.md) and dogfood reviews [#1](../../background/tickets/007-dogfood-review-1-7-aug.md) and [#2](../../background/tickets/013-dogfood-review-2-14-aug.md)

## Context

The what-view's entry shape was frozen in ADR-0002 and its presentation settled by the greybox (ledger, scan-then-expand). Both dogfood reviews passed — assumption 1 survives, the red-team demotion path is moot — leaving four format decisions to lock before the build handoff: granularity, entry shape vs the review findings, per-project file conventions, and ADR-count semantics.

## Decision

**Granularity.** One entry per session, flat, no revisit trigger. Every layer already assumes it (ADR-0002's merge invariant, the greybox's row-per-session ledger, both reviews). A day-level roll-up, if ever wanted, is a render-time grouping, not a storage granularity.

**Entry shape.** Unchanged — the four-section shape stands, with the stated-rationale convention added as an ADR-0002 amendment (prompt-level, regression-gated). No locators on the what-pass.

**Storage.** "One file per project" is retired as a storage convention. The canonical store is structured — one audit table keyed by session, carrying project, date, skip, and the entry markdown; exact schema owned by `to-spec`. The what-view is a cross-project ledger filtered by shared header chrome, so per-project separation is a query, not a file layout. Per-project markdown files are at most a future export; none is specified.

**ADR-count semantics.** Mechanical, never model-extracted: the count of distinct files under the project's `docs/adr/` created or modified during the session, derived from the session's tool events — semantics "ADRs touched", amendments counted the same as creations. An audit surface's numbers must be trustworthy, and a model-emitted count would be the one unverifiable number on the row. Whether the count renders as a badge remains the styled build's call (greybox rider).

## Consequences

- `to-spec` specs the audit table cross-project from the start; the dogfood-era per-project markdown files are historical artifacts, not a format to preserve.
- The build handoff carries three regression-gated prompt repairs: firmer trivial-session SKIP, the anti-capture restatement, and the stated-rationale convention.
- The styled build judges display questions (ADR-count badge, zero-decision-session treatment) against defined semantics rather than inventing them.
