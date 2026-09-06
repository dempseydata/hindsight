# #1 Map: hindsight v1 — plan to buildable

state: closed · labels: wayfinder:map · opened: 2026-08-01 · closed: 2026-08-16

## Destination

Every decision needed to start building hindsight v1 is made — ingest schemas verified against real OTLP/JSONL payloads, the what/why extraction contracts settled with their eval set frozen, and all three views' information architecture validated as greybox prototypes on real harness data. The map closes by handing the pipeline build to `to-spec`/`to-tickets` and entering the Design phase with validated layouts.

## Notes

- Consult: `definition/definition.md`, `definition/command-centre-review.md`, `docs/adr/0001-ingest-listener-not-strict-no-daemon.md`, `definition/red-team.md` + `red-team-tests.md`.
- Eval harness: `eval/` (frozen regression set, ADR-0002 contract; `ideation/eval-why-extractability/` is the dry-run record). Session-derived data goes to `local-data/`, never committed.
- Impeccable hooks OFF during prototype tickets (`/impeccable hooks off`); back on afterwards.
- Plan, don't do — with a narrow execution override for the backfill and dogfood-review tasks only.
- Wedge first: the where-view greybox is deliberately blocked behind both wedge prototypes (red-team sequencing mitigation).
- One ticket per session (research excepted).

## Decisions so far

- [A/B: combined vs separate extraction prompts](003-a-b-combined-vs-separate-extraction-prompts.md) — combined degrades (12/13 vs 13/13 recall, 48% vs 68% evidence integrity, −33% findings); pipeline keeps two separate haiku passes.
- [Lock the extraction contract](009-lock-the-extraction-contract.md) — frozen as ADR-0002: two passes pinned to `claude-haiku-4-5-20251001`; session-global piece indices + sidecar map; why-pass `{change, why, evidence:[{msg, quote}]}`; resolution ladder exact→fuzzy(0.6)→unresolved, model quotes never stored; what-pass markdown as measured.
- [Verify ingest schemas against real payloads](002-verify-ingest-schemas-against-real-payloads.md) — env config, endpoints, tool_decision, delta metrics, usage fields and tool_use_id pairing all confirmed; hook-timing events falsified (no OTEL source — self-instrument or drop, decide at where-view greybox); compaction only inferable via query_source on newer CLIs; verified shapes + constraints in definition/ingest-schema-verification.md.
- [Decide the silent-change backstop](004-decide-the-silent-change-backstop.md) — three sources: project `.claude` git history (commits only), analysis-time snapshots of the `~/.claude` text-config surface (no git there; silent baseline on first run), and structural `installed_plugins.json` diffs; capture at analysis runs only (listener stays ingest-only); content-addressed blobs + one change-event table in SQLite, diffs computed at render; deterministic name+window linking with no model in the loop — no link ⇒ "changed, no stated rationale"; noise filtering is render-time only, policy delegated to the why-view greybox.
- [Decide the backend stack](008-decide-the-backend-stack.md) — ADR-0003: model runner is `claude -p` on subscription (matches the eval transport; analysis runs must self-exclude via config; limit exhaustion is a designed pause (wait for reset; pipeline fails gracefully and resumes), API SDK swap only by operator judgement, no regression needed); listener is stdlib `http.server` with the chunked-body regression test (validation frameworks rejected — optional-by-default telemetry makes strict validation wrong); zero pip deps for pipeline + listener as an ADR-gated default, UI stack explicitly excluded and owned by Design.
- [Freeze the eval set and thresholds](010-freeze-the-eval-set-and-thresholds.md) — frozen in `eval/`: 9 sessions / 4 projects / 15 events incl. a mid-session silent plugin-update day; floors fixed pre-baseline (recall ≥13/15, rationale ≥80%, resolution ≥90%, silent attributions 0, negative-day FPs ≤1); haiku baseline clears all (14/15, 14/14, 97%, 0, 0) — prompt/model changes must match-or-beat it.
- [Run the full-history model backfill](011-run-the-full-history-model-backfill.md) — 207/210 sessions processed (archive depth 2026-06-26→08-01; 44 analysis runs self-excluded), 200 findings / 155 audit entries in `local-data/backfill/`, resolution 97% matching baseline; limit-exhaustion pause+resume worked as designed; new failure mode found: transcript capture on 4 large extract parts — prompt repair rides along with the build handoff, gated by the eval regression.
- [Greybox the what-view (audit log)](005-greybox-the-what-view-audit-log.md) — ledger layout wins (one collapsed row per session: date · title · counts, expand to full entry); the settled content format holds at 53 real entries but journal-style full rendering does not; riders to the Design-inputs bundle: per-entry project identity on rows (implies a cross-project-capable surface) and filtering as a likely shared-header concern; prototype on branch `prototype/what-view-greybox`.

- [Greybox the why-view (change timeline)](006-greybox-the-why-view-change-timeline.md) — day ledger wins (one collapsed row per day: date · headline · counts · projects, drill in); noise policy per #4: churn default-collapsed as counts inside the day, no dimming or toggles; quotes collapsed behind status summaries; riders: per-day stacked type chart with x-axis time filtering, project+time filters compose as shared header chrome; prototype on `prototype/why-view-greybox`.

- [Greybox the where-view](012-greybox-the-where-view.md) — panel dashboard wins (tiles · league with drill · models · latency · MCP · CLI · sunk-cost drill); shared header gains window presets (7/14/28/90/all, default 14d); all sparks share one 30-day axis; hook panel kept for self-instrumentation; pricing and hours/events trimmed; sunk-cost composition drill (ccwhere context_tree, plugins as grouping level) finally lands; found+patched ccwhere's per-install-record skill double-count (fix: key registry by installPath); prototype on `prototype/where-view-greybox`.

- [Dogfood review #1 (~7 Aug)](007-dogfood-review-1-7-aug.md) — done 16 Aug (late, not skipped); entries faithful vs memory, one accuracy finding (culling entry omits the OpenSpec/office-hours rationale — feeds #14), well under the >1-in-10 kill threshold; no actions arising (per calibration, not a failure). Assumption 1 survives review #1.

- [Dogfood review #2 (~14 Aug)](013-dogfood-review-2-14-aug.md) — done 16 Aug (two days late, not skipped); entries faithful per dev (one distorted clause of 11 entries, under the >1-in-10 threshold); trivial session correctly SKIPped unprompted; two-week test closed, assumption 1 survives both reviews; accuracy findings feed Lock the audit format.

- [Lock the audit format](014-lock-the-audit-format.md) — locked as ADR-0004 + an ADR-0002 amendment: one entry per session flat; four-section shape unchanged, no what-pass locators, but Decided lines carry stated rationale (prompt-level, regression-gated — the review-findings fix); "one file per project" retired for one cross-project audit table (schema to `to-spec`); ADR counts mechanical from tool events ("ADRs touched"), badge display stays with the styled build; demotion path moot.

## Not yet specified

- DB schema detail — `to-spec` owns it; extraction contract, stack and audit format are all now settled, so this exits the map with the build handoff. ADR-0004 fixes the audit side: one cross-project audit table keyed by session (project, date, skip, entry markdown), plus the mechanical ADR-count derivation from tool events. The handoff also carries a why-view display note — the why line often near-duplicates the first evidence quote, a possible prompt or render concern — and three ride-along prompt repairs, all eval-regression-gated: the firmer trivial-session SKIP rule (ADR-0002), the anti-capture repair from the backfill (restate why-pass instructions after the transcript), and the stated-rationale convention on Decided lines (ADR-0002 amendment). From the where-view greybox it additionally carries: hook self-instrumentation (a hook POSTing to the ingest listener — the where-view's hook panel is reserved for it), and the context-scan rebuild note (key the plugin registry by installPath; ccwhere's per-install-record scan double-counts skills).
- Why-pass finding categorization — deliberately left out of the frozen shape (ADR-0002); the why-view greybox did not demand grouping, so this is settled as post-v1.
- Config surface specifics (per-view project include/exclude defaults, time windows). Now includes a named requirement from ADR-0003: hindsight's own `claude -p` analysis runs must be excluded from ingestion/analysis by default.
- The Design-inputs bundle: exactly what the validated greyboxes hand to the Design phase. Carries from the what-view greybox: ledger rows need per-entry project identity (row schema includes project even if storage stays one-file-per-project); filtering confirmed as shared header chrome by the why-view greybox (project chips + time controls + per-day type chart); now fully sharpened by the where-view greybox: window presets (last 7/14/28/90/all, default 14d) join the shared header chrome; a single 30-day spark axis across all panels; the cache-read visibility toggle; the sunk-cost composition drill (measured-median-as-authority, plugins as a grouping level) carries into the styled build. Left for the styled build to judge: ADR-count badges (semantics now defined by ADR-0004 — mechanical "ADRs touched" from tool events; only the display question remains), zero-decision-session treatment, the ≥1%-of-tokens chip policy, and the low-volume CLI lump.
- Open-source packaging + model-cost story for strangers (post personal-utility bar). ADR-0003 settles the cost story's core: bring your existing Claude Code auth.

## Out of scope

- UI stack choice — owned by the Design phase exit, not this map.
- All orchestration: task queue, dispatcher, schedules, HITL inbox, Telegram, emergency stop (rejected by name in `command-centre-review.md`).
- Memory curation / AIOS-style harvest loop — parked; ccwhy-successor territory, downstream consumer of hindsight's outputs.
- Public-release scrub and README polish — post personal-utility.






- Process-conformance analysis ("do I follow my stated process? where do I deviate, why, and is the deviation consistent? what does my actual process look like?") — post-first-release enhancement, named 2026-08-03. Nothing rides into the v1 build handoff: raw session JSONL survives in `~/.claude/projects` independently of extraction, and the silent-change backstop's config snapshots already version the stated process (`my-process.md`), so behaviour-vs-process diffing stays possible later.






---

**comment · 2026-08-16**

Map complete — exit condition met. All 13 tickets closed, four ADRs locked (0001–0004), eval set frozen with passing baseline, all three views greyboxed and validated. Build handoff done: spec published as #15, broken into tracer-bullet tickets #16–#24 by to-tickets. Design-phase inputs bundle carried in the spec's further notes. Frontier: #16 + #17.

