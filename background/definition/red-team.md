# Red-team: hindsight definition (2026-07-31)

Attack on `definition.md` per `/red-team-prd`. Upstream evidence: `../ideation/framing.md`, `../ideation/eval-why-extractability/results.md`. Ranked by impact × likelihood × cheapness-to-test.

## Top kill-assumptions

### 1. You will actually *review* the audit trail
Demand evidence for the what-view is borrowed: ccwhere's acted-upon insights were where-view insights, surfaced by a dashboard opened for token reasons. The what-view assumes a new behaviour — rereading a per-project log of past work — the classic journal-nobody-rereads failure.
- **Fails if:** the audit file is written faithfully and read never, or is read and found inaccurate.
- **Test:** dogfood before design — generate the audit for the last two weeks of real sessions in the settled format; use it as the weekly review for two weeks.
- **Kill criterion (revised 2026-07-31 — the what-view is a pseudo audit log, review is the job, actions are a bonus signal not the bar):** demote if either (a) both weekly reviews get skipped, or (b) spot-checking entries against memory finds materially wrong entries (>1 in 10 unfaithful) — a misleading audit is worse than none.

### 2. Why-extractability generalises beyond process-writing sessions
The eval's recorded caveat, now load-bearing: 6/6 detection came from sessions where rationale was dictated aloud while my-process.md was written.
- **Fails if:** on ordinary days (plugin installed mid-task, settings tweak), recall collapses or false positives appear.
- **Test:** identical harness on other projects' sessions from days where git shows a known `.claude`/settings change, plus known-quiet sessions for precision. Also the venue to A/B the "one pass, two outputs" coupling (combined vs separate prompts) before committing to it.
- **Kill criterion:** below the frozen M2/M3 bars on the second corpus → why-view narrows to mechanical detection with model rationale marked speculative.

### 3. Mechanical evidence-span resolution is feasible
The carried constraint assumes fuzzy resolution is easy; the eval showed the model paraphrases and stitches sentences — the hard case for fuzzy matching. Unresolved evidence → findings ship bare → the audit-trust proposition collapses.
- **Fails if:** locator→span resolution succeeds on materially less than ~90% of findings.
- **Test:** fuzzy resolver over the 11 already-committed failed quotes in `outputs/s380.json`.
- **Kill criterion:** <90% → change the contract, not the matcher: model returns message indices carried by the extract, making resolution exact.

### 4. Batch-on-launch analysis is tolerable without a daemon
Eval ran ~40s/session; a backlog is minutes at launch. Friction, not quality, is how new views die — and a stalling app also silently kills assumption 1.
- **Fails if:** typical-day incremental analysis exceeds ~60s, or backlog blocks the where-view from rendering.
- **Test:** benchmark haiku throughput on one real day's sessions; count actual sessions/day from jsonl mtimes.
- **Kill criterion:** >60s typical → design decouples: where-view renders instantly from mechanical parsing; model analysis fills asynchronously with a visible "N sessions unanalysed" state.

### 5. (Sequencing — decidable, not testable) Rebuilding the where-view first is safe
The definition's own future-fit reasoning says where is the commodity and what/why the durable wedge; building the familiar commodity first risks the wedge staying perpetually-next — how ccwhy became a definition with an empty build folder.
- **Mitigation:** tracer-bullet order in `to-tickets` puts the what/why pipeline first; the where-view rebuild comes last.

## Well-reasoned (stated, not manufactured)
Eval-before-design actually followed with frozen thresholds, and it already paid (the mechanical-evidence constraint). Explicit supersession. Read-only posture fences off memory-curation scope creep. Cost-awareness in the right small places: separate refresh controls per cost class, ADR counts not duplicated content, persistence enabling incrementality. Transcript-privacy flagged before it could bite.

## Couldn't assess
UI ambition (no design inputs yet — correctly deferred). Stack (open until design). Open-source viability of the model pipeline (subscription `claude -p` vs a stranger's API key + cost story) — fine at the personal-utility bar, real at publication. "Decisions made, extracted from conversational text" outside ADRs remains the softest phrase; test 1 hardens or kills it.

## Test results
Recorded in `red-team-tests.md` as they run.
