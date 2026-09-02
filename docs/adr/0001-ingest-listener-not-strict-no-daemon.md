# ADR-0001: One ingest-only listener; everything else stays on-demand

**Date:** 2026-08-01 · **Status:** accepted · **Decides:** the tension raised in `definition/command-centre-review.md`

## Context

ccwhere's ADR-0001 ruled "no daemon — on-demand foreground process," written for a product whose only source was files already on disk. Hindsight adds opt-in OTEL telemetry, which is push-based: Claude Code posts OTLP events and does not retry. With no listener running, events are lost permanently — and OTEL uniquely carries edit decisions, hook timings, api-error detail, compactions, precise MCP attribution, and productivity counters. An on-demand-only app therefore means silently gappy metrics in exactly the data OTEL exists to provide; a gappy metric presented as complete is worse than none.

## Decision

Hindsight runs **exactly one background process: an ingest-only OTLP listener** (launchd-managed) that receives `/v1/logs` + `/v1/metrics` and writes to the local SQLite store. Nothing else. It has no UI, calls no model, reads no transcripts, schedules nothing, and orchestrates nothing. The application proper — JSONL sync, model analysis passes, and the dashboard — remains on-demand foreground, per the carried posture.

Boundary test for future additions: if a proposed background capability does anything other than *receive pushed telemetry and persist it*, it belongs in the on-demand app or nowhere. The command-centre prompt's dispatcher stack (task queue, heartbeat, PID management, Telegram) is the named counter-example and is rejected.

## Consequences

- OTEL coverage is continuous from enablement; every OTEL-fed metric still states its coverage window (no pretence of history before enablement).
- The listener must be fault-tolerant per the adopted ingest constraints: per-row try/except, count drops, always return 200.
- Failure degrades gracefully: if the listener is down, JSONL-derived metrics are unaffected; OTEL-fed panels show the gap honestly.
- Supersedes ccwhere ADR-0001's strict form for this product; the *spirit* (no orchestration sprawl) is preserved by the boundary test above.

## Amendment (2026-08-17)

The Context above lists "hook timings" among what OTEL uniquely carries. That claim was falsified during definition (`definition/ingest-schema-verification.md`: hook execution timings — **falsified**; OTEL emits no hook telemetry). Hook timing data comes instead from self-instrumentation: `build/hook.py` POSTs `hindsight.hook` events to this listener — see ADR-0005. The decision itself stands unchanged; do not remove hook.py on the strength of the original sentence.

## Amendment (2026-08-24)

"Schedules nothing" constrains the *listener*: a launchd calendar job that invokes the on-demand analysis command (the nightly, ADR-0008) is a scheduled *invocation* of a foreground process, not a background process, and does not breach the boundary test.
