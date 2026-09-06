# #40 Styled Build of hindsight v1 — what + where views on the on-demand server

state: closed · labels: wayfinder:map · opened: 2026-08-20 · closed: 2026-08-26

## Destination

A working styled UI for hindsight v1 — the what-view ledger and the where-view panel dashboard, plus shared header chrome — served by the on-demand foreground server, built per [design/build-handoff.md](../design/build-handoff.md), with the design ADRs written and the carry-along build items (substrate scan, nightly plist, why-pass removal) resolved.

## Notes

- **Execution is in scope for this map** — build tickets are worked here (via `implement` + `tdd`), not handed off. This overrides wayfinder's plan-only default.
- Inputs, read before any ticket: `design/build-handoff.md`, `design/design-inputs.md`, `design/tokens.css`, `CONTEXT.md`, `docs/adr/`.
- `tokens.css` is the direction contract — committed, inlined by the server at render time, never forked. Comps/artboards are reference only.
- Stack rules (#36, ADR-ready): stdlib `http.server` foreground command, strictly read-only over SQLite; zero-dep vanilla HTML/JS, sparks as inline SVG; no npm, no build step, no CDN. Exceptions require an ADR.
- The honesty rules in design-inputs.md bind every OTEL-fed panel in both views.
- Real data from `local-data/hindsight.db` everywhere — never lorem ipsum.
- The presentation judgement calls in design-inputs.md's "Left to the styled build" are decided **inside** the view tickets against real data and recorded in their resolution comments — not re-litigated, not separate tickets.
- Impeccable hooks stay **on** for this effort (styled build, not greybox).
- The reference canvases ("Hindsight Diverge", "Hindsight Narrow") are **unwatched** as of 2026-08-21 — the live artifact watches died and cannot be re-armed from a build session. Both were last updated 2026-08-20, the handoff date, so tokens.css remains verified. If either canvas is edited later, re-verify tokens.css verbatim against `VariantIndigo.dc.html` before building on it.
- One ticket per session; `code-review` then `/ponytail-review` before each commit.

## Decisions so far

- [Grill-with-docs: interrogate the handoff bundle and write the design ADRs](041-grill-with-docs-interrogate-the-handoff-bundle-and-write-the.md) — ADR-0006 (two-view scope), ADR-0007 (Indigo-deck direction + unwatched-canvas re-verify rule), ADR-0008 (UI stack) written; ADR-0001 amended (scheduled invocation ≠ background process); CONTEXT.md reframed to two views and pruned wholesale. Commit a0aeb5c. Housekeeping: #46 closed as botched duplicate of #48; nightly plist ticketed as #49.
- [Richer substrate scan: consumer grain, error flags, message-lens token linkage](042-richer-substrate-scan-consumer-grain-error-flags-message-len.md) — all grains landed and backfilled (93 sessions rescanned, 11,725 grain rows); consumer classification ported from ccwhere's validated parse; streamed-duplicate tool_use rows deduped and the #38 malformed-name wart rejected at parse time; pruned-transcript rows read NULL (unknown), never zero. Message-lens join-key call deferred to the where-view ticket. Commit 5242ebb.
- [Remove the why-pass from analyze.py and the schema](043-remove-the-why-pass-from-analyze-py-and-the-schema.md) — clean cut per ADR-0006: pipeline code, prompts, eval harness, and the findings/evidence/runs tables gone; existing rows **dropped** (raw model outputs stay cached under local-data/, so re-derivable); backstop capture and eval/extract.py kept; MODEL pin now lives in analyze.py; backfill.py (completed one-off) deleted with it. Commit 8cdf8be.
- [Server skeleton and shared header chrome](044-server-skeleton-and-shared-header-chrome.md) — `build/serve.py` live: read-only stdlib server on :8321, tokens.css inlined per request, full chrome (chips, stacked per-day chart, click-a-bar filtering, presets, cache-read toggle) verified in-browser on real data. Chip policy judged: non-path names clearing ≥1% of all-time tokens **or** sessions — 8 chips, 17 tail. Views mount via `hs.onFilter`. Commit c6f2af9. Housekeeping: review residue from #41–#43 filed as #50 (needs-triage, off this route).
- [What-view: the styled session ledger](045-what-view-the-styled-session-ledger.md) — `/what` live and browser-verified on 250 real sessions: row-per-session ledger with `<details>` expansion, day roll-up at render time, both entry shapes parsed. Judged: ADR count renders as a conditional accent badge only when ≥1 (7 of 240 nonzero — a column would be 97% blank); zero-decision sessions read as three dim populations (SKIP one-liners, #38 refusal rows with raw text tucked in the expansion, "0 decided" counts) and stay scannable. Added for honesty: synced-but-unanalyzed and undated sessions render as dim rows, never silently dropped. Commit 157011a. Housekeeping: #44-chrome review residue appended to #50; axis-contrast flag left for #47.
- [Where-view: the styled panel dashboard](048-where-view-the-styled-panel-dashboard.md) — `/where` live and browser-verified on real data: all seven panels on the shared chrome, dual-lens consumer league over the #42 grains (message-lens joins on `message_id` alone), models + OTEL latency, MCP/CLI tables, sunk-cost medians as authority, ADR-0005 hook panel. Judged: coverage gaps render as shaded spark regions (hybrid with one global line, no banner walls); CLI lump row collapses on an all-time <5-call floor; league membership ≥5 all-time calls with a visible tail; errors/day sparks ruled semantic (`--o-problem`). Commit b5c2a2c.

- [Floor audit: /impeccable audit over the styled UI](047-floor-audit-impeccable-audit-over-the-styled-ui.md) — one floor violation found and fixed: 9px chart-axis text in `--o-axis` (3.99:1) → `--o-dim` (7.02:1), tokens.css untouched; all other floor rules verified passing, audit health 18/20. Non-floor P2 (mouse-only chart filtering) appended to #50. Commit e2a730f.

- [Nightly analysis launchd calendar job](049-nightly-analysis-launchd-calendar-job.md) — `analyze.py install`/`uninstall` subcommands generate and bootstrap a `com.hindsight.nightly` 03:00 `StartCalendarInterval` plist (installing shell's PATH baked in so `claude` resolves under launchd); sandbox blocked `launchctl bootstrap`, so the operator runs `python3 build/analyze.py install` once. Commit b15ccff. Review residue (empty-DB chrome RangeError) appended to #50.

- [Post-build capture: record the shipped UI's design system as a product DESIGN.md?](052-post-build-capture-record-the-shipped-ui-s-design-system-as.md) — yes: derived product DESIGN.md at repo root (Impeccable documenter, post-#47 surface) so the hooks' design-system drift detection is no longer inert; tokens.css stays sole authority (conflict → tokens.css wins; re-derive on visual change); recorded as an ADR-0007 addendum; design.json sidecar generated but untracked. Commit 9e06ab4.

## Not yet specified

Nothing — the route is complete: no open tickets remain and the destination is reached (#52 was the last).

## Out of scope

- The why-view surface and its standing eval burden — dropped from v1 per #39. The silent-change backstop *capture* stays but renders nowhere.
- Defect #38 (refusal-text audit rows) and bug #29 (truncated live-session extracts) — independently tracked bugs, not on this route. The what-view should tolerate #38's rows, not fix them.
- [Deleted projects and the evolving collection](051-deleted-projects-and-the-evolving-collection-hide-in-navigat.md) — tabled 2026-08-25 for a discussion **after** this map completes: hide on the navigation side, never remove data. The view tickets should not partially solve this (e.g. no ad-hoc hiding of gone projects); the chrome's all-time chip policy stands until that chat.












---

**comment · 2026-08-26**

Route complete: destination reached — both styled views, shared chrome, on-demand server, design ADRs, and all carry-alongs (substrate scan, why-pass removal, nightly plist, floor audit, DESIGN.md capture) resolved. All child tickets closed; last was #52.

