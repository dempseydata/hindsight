# Hindsight — definition

**Date:** 2026-07-31
**Upstream:** `../ideation/framing.md` (premise, supersessions), `../ideation/eval-why-extractability/results.md` (confirmed wedge + constraints)
**Status:** Draft, awaiting attack (`/red-team-prd` or `/pre-mortem`) before Design.

## What it is

One local application over Claude Code data, answering three questions for a solo, skill-heavy operator. Two ingest sources: the JSONL transcripts already on disk (`~/.claude/projects/*.jsonl`, plus `.claude/` config trees) as the archive with months of backfill, and **opt-in OTEL telemetry** (added 2026-08-01, see `command-centre-review.md`) as the enrichment feed — it uniquely carries edit accept/reject decisions, hook timings, api-error detail, compactions, precise MCP attribution, and commit/PR/LoC counters. OTEL-fed metrics state their coverage window honestly; ingestion runs as a minimal always-on **ingest-only listener** — the single sanctioned background process (decided 2026-08-01, `docs/adr/0001-ingest-listener-not-strict-no-daemon.md`); everything else stays on-demand.

| View | Question | Provenance |
| --- | --- | --- |
| **Where** | Where did my tokens go? | Rebuild of ccwhere's shipped scope |
| **What** | What did I actually do? | New — the hindsight wedge |
| **Why** | Why did my process change? | New — ccwhy's observability half, eval-confirmed |

Sole v1 user is the operator; open-source publication follows personal utility, as with ccwhere.

## Scope per view

**Where** — token input/output/cache-creation/cache-read per session, day, and project; session-start sunk cost itemised per project (CLAUDE.md chain, skill descriptions, MCP schemas); per-skill, per-MCP, per-CLI usage counts and tokens per call. Known-buildable; UI to be redesigned rather than ported.

**What** — a reviewable audit trail per session/day/project: actions taken (files changed, commands run, artifacts produced, commits made) and decisions made (extracted from conversational text). Granularity and review cadence are the softest part of this definition — expected to firm up in Design/spec, flagged for the attack.

**Why** — a setup-evolution timeline: detected changes to skills, plugins, process docs, standards, and config, each with when, what, and the inferred driver, evidenced by verbatim transcript spans.

## Constraints carried in (not up for casual re-litigation)

From the 2026-07-31 eval, hard:

1. **Evidence is attached mechanically.** The model proposes findings with approximate locators; the pipeline resolves them to true spans and stores verbatim text + source offset. Model-quoted text is never stored as evidence.
2. **Why-inference runs on a cheap model** (haiku-class) over extracted conversational text only (user + assistant text blocks — tool results excluded; detection survived that cut at 6/6).
3. **Mechanical detection backstops the model.** Silent setup changes (config edits with no conversation) are untested territory; file/config diffing must detect what the model can't.

From ccwhere's ADRs — presumed carried, each may be deliberately re-litigated in Design with an ADR:

- Read-only observability. The app never changes the Claude Code setup, never orchestrates, never auto-optimises. (Also why memory curation stays parked.)
- No daemon — on-demand foreground process.
- Local only: no cloud, accounts, auth, or outbound telemetry. Localhost UI.
- No proxy/interception; reads what is already on disk; full-history backfill on first run.
- Attribution heuristics are labelled as such; no billing-grade cost accounting.
- *Re-litigation candidates:* stdlib-only (may conflict with the intended UI upgrade and model-inference pipeline); port/packaging choices.

## Non-goals

- No memory curation or feedback into Claude Code (parked; possibly a later product on top of the why-view).
- No orchestration, scheduling, or approvals.
- No automatic optimisation — hindsight diagnoses, the operator decides.
- Transcript privacy: transcripts and derived evidence never leave the machine; repo hygiene keeps session text out of the published codebase (the ideation eval extracts must be stripped before open-sourcing).

## Config (new relative to ccwhere)

- Which projects appear in views by default (include/exclude, per view).
- Sensible defaults for time windows and view landing state.
- Config is a file the operator edits or a settings surface — not accounts, not sync.

## Dual purpose (load-bearing)

This build is also the end-to-end shakedown of the rebuilt process (my-process.md): ideate → design → build → deploy, run honestly, through to a deployed app. Process friction discovered en route is itself a deliverable — exactly the material the why-view exists to record.

## Evaluation moments ahead (per the discipline)

- **Before implementing the why-view:** freeze an eval set from real transcript history with a numeric bar (the 2026-07-31 run is the seed; extend with silent-change days).
- **On any prompt/model change:** regression against the standing set.
- **Before deploy:** quality gate beside `security-preflight`, plus cost-per-analysed-day ceiling.
- **After deploy:** a usage measure (do I actually open it weekly?) and a model-quality measure (spot-check rate of accepted vs corrected why-findings).

## Settled 2026-07-31 (operator decisions on the draft's open questions)

1. **What-view granularity:** one audit file per project, reverse chronological (newest first). Decisions are *counted, not duplicated* — the project's own ADRs hold the detail; the audit log records e.g. ADRs added / changed / reviewed-unchanged / deleted per session/day.
2. **Derived findings are persisted** in a local store (SQLite precedent from ccwhere).
3. **Stack:** deferred to Design — decided by what the design phase demands.
4. **Analysis trigger:** batch on launch plus a manual refresh — but a *separate* refresh control from the where-view's token-metrics refresh; the two are different costs and different cadences and must not share a button.
5. **Two separate model passes** (reversed 2026-08-01 by the A/B on the eval corpus — [issue #3](../tickets/003-a-b-combined-vs-separate-extraction-prompts.md)): the combined pass dropped a ground-truth event, found 33% fewer real items, and halved evidence integrity — attention-splitting under compression. The original "one pass, two outputs" preference lost to the data; the sub-cent-per-session saving didn't buy back a lost event. Final contract formalised in map ticket #9.
6. **Prototype-first sequencing (adopted 2026-07-31, now the process default for dense tool UIs):** pipeline first, then greybox prototypes of the three views with real data to settle information architecture, *then* the Design phase, then styled UI. Composes with the red-team's build-order mitigation (wedge first, where-view rebuild last). Guardrails in `.claude/my-process.md` — Design deferred is not Design skipped.
