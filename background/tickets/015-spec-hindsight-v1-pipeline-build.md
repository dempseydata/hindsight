# #15 Spec: hindsight v1 pipeline build

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Problem Statement

Months of Claude Code history sit on disk, and every design decision needed to use it has been made — the extraction contract is frozen (ADR-0002), the stack is settled (ADR-0003), the audit format is locked (ADR-0004), the eval set is frozen with a passing baseline, and all three views have validated greybox layouts. But there is no product. The full-history backfill's findings and audit entries live in throwaway prototype JSONL files; opt-in OTEL telemetry is being lost permanently whenever no listener is running, because Claude Code does not retry; silent config changes are not being snapshotted, so the mechanical backstop has no history accumulating; and there is no durable store for the Design-phase UI to read from. Every day without the pipeline running is telemetry lost and snapshot history not taken.

## Solution

Build the hindsight v1 backend: one SQLite store and the on-demand analysis run that fills it, plus the single sanctioned background process — the launchd-managed ingest-only OTLP listener. The analysis run syncs JSONL transcripts, runs the two frozen extraction passes over new sessions via `claude -p`, resolves evidence to verbatim transcript spans, snapshots the config surface and derives change events, and computes mechanical ADR counts. The operator gets a store that answers all three views' questions (where / what / why) cross-project, honestly gapped where coverage is missing, with hindsight's own analysis sessions excluded. The Design phase then builds the styled UI on top of a working, populated store.

## User Stories

1. As the operator, I want an always-on OTLP listener receiving `/v1/logs` and `/v1/metrics`, so that edit decisions, api-error detail, MCP attribution, and token metrics are captured continuously from enablement instead of being lost.
2. As the operator, I want the listener managed by launchd, so that it survives reboots without me remembering to start it.
3. As the operator, I want the listener to accept chunked transfer-encoded JSON bodies, so that real Claude Code payloads are not silently read as zero bytes.
4. As the operator, I want the listener to treat every payload attribute as optional, keep whatever arrives, count-and-skip what it cannot parse, and always return 200, so that CLI version variance never causes dropped telemetry or client-side errors.
5. As the operator, I want JSONL-derived metrics to be unaffected when the listener is down, and OTEL-fed data to state its coverage window, so that a gap is shown honestly rather than presented as a zero.
6. As the operator, I want an on-demand analysis run that syncs new transcripts from `~/.claude/projects` and processes only sessions not yet analysed, so that repeated runs are cheap and idempotent.
7. As the operator, I want hindsight's own `claude -p` analysis sessions excluded from ingestion and analysis by default, so that the tool does not observe itself into the data.
8. As the operator, I want the analysis run to recognise subscription-limit exhaustion, leave remaining sessions marked unanalysed, and resume cleanly on the next run, so that hitting limits is a pause rather than a failure.
9. As the operator, I want each analysed session to produce why-pass findings shaped `{change, why, evidence}`, so that the why-view has structured setup-change material.
10. As the operator, I want every stored evidence span to be verbatim transcript text resolved through the exact→fuzzy(0.6)→unresolved ladder, never the model's quote, so that evidence is substring-verifiable against the real transcript.
11. As the operator, I want unresolved evidence kept and marked rather than dropped, and the per-run resolution rate recorded against the 97% eval baseline, so that extract or prompt drift shows up as a health metric, not silent decay.
12. As the operator, I want one audit entry per session in the four-section markdown shape, with trivial sessions stored as SKIP, so that the what-view ledger has one row per session with noise filtered at the source.
13. As the operator, I want Decided lines to carry stated rationale as close paraphrase or quote, and nothing invented when none was stated, so that the audit trail reflects what actually happened.
14. As the operator, I want multi-part sessions merged into a single audit entry, so that the one-entry-per-session invariant holds at any transcript size.
15. As the operator, I want the audit store to be one cross-project table keyed by session, so that per-project separation is a query and the what-view can filter by shared header chrome.
16. As the operator, I want ADR counts derived mechanically from the session's tool events as "distinct files under `docs/adr/` touched", so that the one number on an audit row is trustworthy rather than model-emitted.
17. As the operator, I want each analysis run to snapshot the `~/.claude` text-config surface, diff project `.claude` git history, and diff `installed_plugins.json` structurally, so that silent setup changes are detected without any conversation mentioning them.
18. As the operator, I want config content stored as content-addressed blobs with one change-event table, diffs computed at render time, so that history is compact and the first run establishes a silent baseline.
19. As the operator, I want change events linked to why-findings by deterministic name-and-window matching with no model in the loop, so that an unlinked change honestly reads "changed, no stated rationale" instead of getting a fabricated driver.
20. As the operator, I want the three regression-gated prompt repairs (firmer trivial-session SKIP, anti-capture restatement after the transcript, stated-rationale on Decided lines) landed with a passing `eval/run.sh` result recorded, so that the known failure modes are fixed without regressing the frozen floors.
21. As the operator, I want findings and audit rows to carry the prompt version and model that produced them, so that backfilled history and repaired-prompt output coexist legibly.
22. As the operator, I want the existing backfill's cached model outputs imported into the store rather than re-extracted, so that 207 sessions of history do not cost a second pass through subscription limits.
23. As the operator, I want token usage (input/output/cache-creation/cache-read) queryable per session, day, and project from JSONL, so that the where-view's core panels have their data regardless of OTEL coverage.
24. As the operator, I want tool-use events with names, ids, and timestamps stored per session, so that per-skill, per-MCP, and per-CLI usage counts and the ADR-count derivation all read from one place.
25. As the operator, I want the session-start sunk-cost scan to key its plugin registry by install path, so that skills under multiple install records are not double-counted.
26. As the operator, I want a hook that POSTs its own timing to the ingest listener, so that the where-view's hook panel has a source OTEL does not provide.
27. As the operator, I want a config file controlling per-view project include/exclude and default time windows, with self-exclusion of analysis runs as a named default, so that view defaults are mine to set without touching code.
28. As the operator, I want the why-view's analysis refresh and the where-view's metrics refresh to be separate operations, so that a cheap metrics reload never triggers model spend.
29. As the operator, I want everything to run on stdlib Python only, so that install stays clone-and-run and nothing breaks silently on a Python upgrade.
30. As the operator, I want all data local — transcripts, evidence, and OTEL tables (which carry account identifiers and prompt text) never leaving the machine — so that the privacy stance survives the build.

## Implementation Decisions

- **Modules.** The ingest listener (the one background process); the analysis run (one on-demand entrypoint: JSONL sync → extraction → resolution → backstop snapshot/diff → ADR counts → assemble); the store (single SQLite file); the config surface (one operator-editable file); the self-instrumentation hook; the sunk-cost context scan. The eval harness stays as-is and is not part of the product.
- **Store schema** (owned by this spec per ADR-0004; shapes derived from the backfill prototype's record formats):
  - `sessions` — session id (PK), project, transcript path, date, CLI version, size, analysis status (`pending` / `empty` / `partial` / `done`), timestamps.
  - `audit` — session id (PK), project, date, `skip` flag, entry markdown, ADR count, prompt version, model. One row per session, cross-project (ADR-0004).
  - `findings` — id, session id, project, date, change, why, prompt version, model.
  - `evidence` — finding id, msg index, source uuid, status (`exact` / `fuzzy_msg` / `fuzzy_global` / `unresolved`), verbatim span (NULL when unresolved). Shape from the backfill prototype's resolver.
  - `otel_events` — event name, session id, timestamp, full attributes as JSON. `otel_metrics` — metric name, timestamp, value, attributes as JSON. Only event name and session id load-bearing; everything else optional-by-default. Marked sensitive (account identifiers, prompt text).
  - `blobs` — sha256 (PK), content. `change_events` — id, observed-at, source (`project-git` / `snapshot` / `plugins-structural`), path, before/after blob hashes, linked finding id (nullable).
  - `tool_events` — session id, tool-use id, tool name, timestamp, file path where applicable — the JSONL-derived substrate for ADR counts and per-skill/MCP/CLI counts.
  - `usage` — session id, timestamp, model, input/output/cache-creation/cache-read tokens, from JSONL assistant records.
  - `runs` — analysis-run bookkeeping: started/ended, sessions processed, resolution-status counts (the standing health metric), limit-pause flag.
- **Extraction** is ADR-0002 verbatim: two separate passes per session extract, model pinned `claude-haiku-4-5-20251001`, transport `claude -p`, 180K-char chunk cap, session-global piece indices with a sidecar index→uuid map, per-part why-pass concatenation, what-pass per-part plus one merge call. The backfill prototype's extract format, fence-stripping, validity checks, and resolution ladder carry over as the reference implementation.
- **Prompt repairs** ride with this build as prompt edits, each landing only on a passing frozen-eval regression: firmer trivial-session SKIP, restated why-pass instructions after the transcript (the anti-capture repair — 4 of 207 backfill sessions captured the transcript on large parts), and stated rationale on Decided lines. Prompts are versioned; rows record which version produced them.
- **History import, not re-extraction.** The backfill's cached per-session model outputs are assembled into the store under their original prompt version. Sessions the backfill left partial or that post-date its snapshot are analysed fresh.
- **Silent-change backstop** per the map's decision: capture at analysis runs only (the listener stays ingest-only); three sources (project `.claude` git commits, snapshots of the `~/.claude` text-config surface, structural `installed_plugins.json` diffs); first run is a silent baseline; linking to findings is deterministic name+window matching; noise policy is render-time and out of this spec.
- **ADR counts** are computed from `tool_events` at assemble time: distinct paths under the project's `docs/adr/` written or edited in the session. Never model-derived.
- **Limit exhaustion** is detected from the `claude -p` failure surface, marks the session unanalysed, stops the run cleanly, and the next run resumes — the backfill's rename-to-`.bad`-and-retry behaviour, promoted to the product.
- **Config** is one file: per-view project include/exclude, default time windows, listener port. Analysis-run self-exclusion (by prompt signature, as in the backfill) is a built-in default, not merely a config entry.
- **Self-instrumentation hook** POSTs hook name and duration to the listener's ingest endpoint; stored alongside OTEL events. If the listener is down the hook fails silently and fast — hooks must never slow a session.
- **Zero pip dependencies** (ADR-0003): `sqlite3`, `http.server`, `subprocess`, `difflib`, `hashlib`, `json`. Any exception needs a new ADR. UI stack excluded — Design owns it.

## Testing Decisions

- Good tests here assert external behaviour at the two agreed seams; no tests of internals below them.
- **Seam 1 — listener HTTP boundary.** Start the listener on a test port, POST real captured OTLP payloads — including a chunked transfer-encoding body (the regression ADR-0003 names, from the capture stub that silently read zero bytes) and a malformed row — and assert the SQLite rows, the skip counters, and the unconditional 200s.
- **Seam 2 — analysis-run entrypoint.** Run the full analysis over a fixture data directory (transcripts shaped like the verified JSONL, a config surface to snapshot, an ADR touch in tool events) with the model runner stubbed to canned outputs. Assert findings and evidence rows with correct resolution statuses (exact, fuzzy, unresolved all exercised), audit rows including a SKIP and a multi-part merge, change events with and without a linked finding, ADR counts, self-exclusion, idempotency of a second run, and the limit-exhaustion pause-and-resume path via a stub that fails mid-run.
- **Prompt and model quality** is not tested at either seam: the frozen `eval/run.sh` set owns it, and each of the three prompt repairs lands with its recorded regression result.
- Prior art: the eval harness's scoring approach (normalised substring verification), the backfill's `.bad`-retry idempotency, and the capture stub's chunked-body lesson.

## Out of Scope

- All three view UIs, their styling, and the UI stack — the Design phase owns them; the greybox prototypes' code dies per the prototype-first guardrails.
- Display judgements deferred to the styled build: ADR-count badges, zero-decision-session treatment, the ≥1%-of-tokens chip policy, the low-volume CLI lump, why-view noise rendering.
- Why-pass finding categorization (settled post-v1 by the why-view greybox).
- Process-conformance analysis (named post-first-release).
- Open-source packaging, public-release scrub, README polish.
- Per-project markdown export of audit entries (at most a future export; none specified).
- All orchestration: task queues, schedulers, HITL, notifications (rejected by name in the command-centre review).
- Memory curation / feedback into Claude Code (parked).

## Further Notes

- Build order for `to-tickets` should honour the red-team sequencing: wedge first (store + listener + extraction), where-view data substrate last.
- The Design-inputs bundle (shared header chrome, window presets, single 30-day spark axis, sunk-cost drill, cache-read toggle) is a map deliverable riding alongside this spec, not part of it.
- Known render/prompt concern carried to Design: the why line often near-duplicates the first evidence quote.
- Compaction detection via `query_source` and OTEL↔JSONL joins via `tool_use_id` are CLI-version-gated; the schema stores what arrives and derivations degrade gracefully (verified-shapes doc).
- OTEL tables are sensitive (account identifiers, prompt text when detail flags are on) — exports and screenshots must treat them accordingly.



---

**comment · 2026-08-16**

## Build order (operator's run sheet)

One ticket per session: `/clear`, then **"implement #N"**; close the ticket when committed and reviewed. If a session fails, the ticket stays open — retry it next session; the order doesn't change. Native blocked-by relationships enforce the edges if anything is grabbed out of turn.

| Session | Ticket | Why this position |
|---|---|---|
| 1 | #16 Ingest listener | Every day it isn't running is OTEL data lost forever |
| 2 | #17 Analysis-run skeleton | The trunk — three tickets hang off it |
| 3 | #18 Why-pass + evidence | Completes the extraction wedge |
| 4 | #19 Prompt repairs | Land fixed prompts before analysing new sessions |
| 5 | #20 Backfill import | History flows into the store |
| 6 | #21 Silent-change backstop | Snapshots start accumulating — later is worse |
| 7 | #22 Where-view substrate | Tokens, tool events, ADR counts |
| 8 | #23 Hook self-instrumentation | Small; needs only the listener |
| 9 | #24 Sunk-cost context scan | Deliberately last (red-team build order: where-view substrate trails the wedge) |


---

**comment · 2026-08-17**

Run sheet complete: all nine tickets (#16–#24) closed in order, each committed and reviewed in its own session. The v1 pipeline stands — ingest listener, extraction wedge (what/why passes, v2 prompts, regression-gated), backfill (207 sessions), silent-change backstop, where-view substrate (tool events, usage, ADR counts), hook self-instrumentation, sunk-cost scan. 65 seam tests green. Standing health metrics live: per-run resolution rate against the 97% eval baseline, coverage window on OTEL-fed metrics.

Follow-ups filed from the final ticket's review: #25–#28 (hook honesty/boundedness, ADR-0001 correction). Next phase: real end-to-end analysis run over the live archive, then a wayfinder charting session for the three views (prototype-first, per .claude/my-process.md).

