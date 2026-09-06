# Input review: the "command centre" build prompt + AIOS intake skills

**Date:** 2026-08-01. Reviewed before wayfinder charting, at the operator's request.
**Sources:** a public "Build Your Own Claude Code Dashboard" prompt (full-stack command centre: JSONL + OTEL ingest, FastAPI/SQLite, React dashboard, task dispatcher, Telegram); the "AIOS Self-Improvement Starter" skills (`improvement-intake-planner`, `data-intake`). Python files not reviewed (not supplied).
**Operator's steer:** no skill-launching/orchestration wanted; the action-insight panels and always-on OTEL ingestion are the attraction.

## Adopted into scope

### OTEL telemetry as a second data source (opt-in)

> **Verified against real payloads 2026-08-01** — see `ingest-schema-verification.md`. Two corrections: hook execution timings do **not** exist in OTEL (falsified), and compaction has no dedicated event (inferable only via `query_source: "compact"` on newer CLI versions).

Config lives in `~/.claude/settings.json`: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, OTLP/HTTP JSON endpoint pointed at the local app, `OTEL_LOGS_EXPORTER=otlp`, `OTEL_METRICS_EXPORTER=otlp`, `OTEL_LOG_TOOL_DETAILS=1`. Setup must merge-not-overwrite and back up the file first.

Not redundant with JSONL — OTEL uniquely carries: `tool_decision` (edit accept/reject), hook execution timings, `api_error` detail with attempt counts, compaction events, precise MCP server/tool attribution, and the `claude_code.{commit,pull_request,lines_of_code}.count` counters. JSONL remains the archive (months of backfill, no config needed); OTEL is the enrichment feed from enablement forward. Every OTEL-fed metric must state its coverage window honestly — no pretending the feed reaches back before it was turned on.

### Insight candidates, mapped to views

| Insight | View | Source | Note |
| --- | --- | --- | --- |
| Cache efficiency: `cache_read / (input + cache_read + cache_create)`, 70% target, low-sample badge <10K billable | where | JSONL | |
| Per-tool latency p50/p95/max + error rate + N | where | JSONL pairing, OTEL when on | |
| Hook activity: fires + paired durations (start/complete FIFO per session, 60s cap) | where | OTEL | standing overhead ccwhere never measured |
| MCP per-server/per-tool drill-down; schema token cost | where | OTEL precise, JSONL `mcp__s__t` fallback | ccwhere scope, richer sourcing |
| Skill economics; context health (CLAUDE.md/settings scan, no LLM) | where | files + JSONL | ccwhere scope |
| Pressure: retry exhaustion, compactions, recent api errors | where | OTEL | |
| Session outcomes: mutually exclusive daily buckets, priority `errored > rate_limited > truncated > unfinished > ok`, stacks sum to day total | what | JSONL | |
| Productivity counters: commits, PRs, lines ±. Delta-counters — `SUM(value)` is correct | what | OTEL | makes audit-log "Did" counts partly mechanical |
| Agent fanout: sessions dispatching the Agent tool | what | JSONL | |
| Crashed/failed session surfacing (stderr + `is_error`) | what | JSONL | |
| Edit acceptance: accept/reject for Edit/MultiEdit/Write/NotebookEdit, low-sample badge N<10 | what | OTEL `tool_decision` | a *mechanical* slice of the 2026-07-21 "how" dimension — allowed in scope precisely because it needs no LLM interpretation; the LLM-interpretive "how" remains a separate future tool |

### Implementation scar tissue (adopt as build constraints)

- **Local-time day bucketing everywhere** — UTC bucketing misattributes evening sessions.
- **`tool_use`/`tool_result` pairing by `tool_use_id`; cap duration at 10 min** (longer = orphan from a crashed session).
- **OTLP ingest is fault-tolerant**: per-row try/except, count drops, always return 200 — Claude Code does not retry; one malformed event must never drop a batch.
- Session title = last user message; fall back to session id, visibly muted.
- Strip home dir by regex, never a hardcoded username.
- Relative times with absolute on hover; skeletons not spinners; empty states that teach.

## Rejected, by name

The entire orchestration half: task queue/dispatcher, schedules, HITL decisions/inbox, live-session stdin messaging, Telegram bridge, emergency stop, skill autonomy controls. Hindsight's standing non-goal (read-only; the operator decides) — and the prompt itself demonstrates the dragged-in surface: launchd process trees, PID marker files, notification dedupe, markdown-parse retry loops. None of it observes anything; all of it acts.

**Validation note:** this maximal dashboard contains no why-view and no audit trail — nothing reconstructs rationale or setup evolution. Hindsight's wedge survives contact with the richest command-centre example available.

## AIOS intake skills: adjacent, out of scope

`improvement-intake-planner` + `data-intake` harvest *external* MCP sources for drift/correction/demand signal, feeding a chain that ultimately changes skills/context — the actuator side, adjacent to the parked memory-curation territory, not to observability. Out of v1 scope.

Two things worth keeping from them:

1. **The connection:** hindsight's outputs (audit log, why-timeline) are exactly the evidence a future improvement loop would consume. If that loop is ever built, it sits downstream of hindsight, separate, as ccwhy's successor.
2. **The trust posture:** propose-disabled / human-enables / versioned policies — the same pending-until-confirmed model hindsight v1 used for memories. Reuse when anything in hindsight ever proposes rather than reports.

## The tension raised: always-on OTEL vs no-daemon (ccwhere ADR-0001)

OTEL is push; Claude Code doesn't retry; no listener means events lost forever. On-demand-only means permanent gaps in exactly the metrics OTEL uniquely carries — and a silently gappy metric is worse than none. Options:

- **(a) Keep no-daemon strictly:** OTEL is best-effort enrichment, gaps labelled.
- **(b) Minimal exception (lean):** an ingest-only listener — launchd-managed, OTLP→SQLite, no UI, no LLM, no orchestration, tens of lines — while the app proper stays on-demand. The no-daemon rule was written for ccwhere, which had no push source; a single-responsibility listener is not the sprawl it defended against.

**Decided 2026-08-01: option (b)** — recorded as `docs/adr/0001-ingest-listener-not-strict-no-daemon.md`, with a boundary test to keep the exception from widening. The dispatcher remains rejected.

## Code review: the AIOS py files (supplied 2026-08-01)

The scripts confirm the out-of-scope verdict (they are batch pull adapters, no listener, no overlap with hindsight's ingest) — but the deterministic core is well-made and four patterns transfer to hindsight's build as constraints:

1. **One enforcement point.** `intake_lib` is the single place the land/dedupe/state contract lives; every adapter calls it. Hindsight's equivalent: one core lib owning session upsert, tool-call pairing, and derived-finding idempotency — sync scripts and the listener both call it, the contract is never re-implemented.
2. **Idempotent landing with bounded state.** Dedupe by stable id, re-runs land nothing, seen-set capped (their 5000-id tail). Hindsight's analysis passes must behave the same: re-analysing a session never duplicates findings.
3. **Never half-write.** Sidecar written before envelope; collision suffixes instead of clobbering. Same rule for hindsight's evidence spans and audit entries.
4. **Self-check in `__main__`.** `intake_lib` proves its own dedupe in a tempdir on direct invocation. Cheap, framework-free, worth copying as house style for every deterministic core script.

Flaws to avoid repeating: state files written non-atomically (no tmp+rename — a crash mid-write corrupts dedupe state; hindsight's SQLite/WAL sidesteps this, but any JSON checkpoint must write-then-rename); the hand-rolled YAML envelope quoting is naive (a title containing a double quote breaks it — use a real serialiser); `run_intake.py` imports pyyaml while the README claims stdlib-only (a copied-doc drift of exactly the kind hindsight's why-view exists to catch); content-hash event ids mean an edited file re-lands as a new event (fine for their intake, wrong for hindsight's re-parsed sessions — key on session id + stable offsets, not content hashes).
