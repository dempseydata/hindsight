# ADR-0005: Hook self-instrumentation — source, bounds, and what the numbers mean

**Date:** 2026-08-17 · **Status:** accepted · **Decides:** the deferred hook-activity sourcing question from `definition/ingest-schema-verification.md`, plus the timing-semantics and boundedness findings in [#25](../../background/tickets/025-hook-py-unbounded-stdin-read-can-stall-a-session-despite-the.md)–[#27](../../background/tickets/027-hook-duration-ms-measures-the-instrument-not-the-session-s-c.md)

## Context

The where-view's hook panel was specced with its source deliberately undecided: OTEL was assumed to carry hook timings, and definition-phase verification falsified that (ADR-0001 is amended accordingly). The options were self-instrumentation — a hook that reports its own firings to the ingest listener — or dropping the insight. Ticket #23 built the hook; the ticket-#24 review then showed its stated guarantees were looser than its docstring claimed: the 0.5s "hard bound" applied per socket operation rather than in total, the unbounded `stdin.read()` sat outside any bound, and `duration_ms` was glossed as the firing's wall cost when it measures only the script body.

## Decision

**Source.** The hook panel's only data source is `build/hook.py`, registered per hook event in `~/.claude/settings.json`, POSTing one `hindsight.hook` OTLP record per firing to the ingest listener. This does not breach ADR-0001's one-background-process boundary: the hook is a short-lived per-event process spawned by Claude Code, not a resident daemon, and the listener still only receives-and-persists.

**Boundedness.** `TIMEOUT` is a per-leg budget, not a total. Every blocking leg — the stdin wait (a `select`-guarded bounded read), the connect, the response wait — is individually capped, so the worst case is a small multiple of `TIMEOUT`, never an unbounded stall. The response body is discarded unread. Failure is silent by design: no error ever surfaces into a session, which means a misconfigured hook is indistinguishable from a dead listener at the session surface — the panel's coverage honesty (ADR-0001's coverage-window rule) is the compensating control.

**What the numbers mean.** `hook.cpu_ms` (process CPU including interpreter startup) is the per-firing cost figure the panel charts. `hook.duration_ms` measures the script body only — its clock starts after spawn + interpreter startup and stops before the POST — and must never be presented as the session's cost of a firing. The true wall cost (spawn to exit, including any timeout waits) is visible only to the spawning harness and is not captured; the panel states this rather than substituting a proxy.

**Volume.** The recommended registration is the three low-frequency events (SessionStart, UserPromptSubmit, Stop). Registering PostToolUse multiplies rows per session by tool-call count and makes the instrument a dominant writer to the store it measures — allowed, but a deliberate choice, not the default.

## Consequences

- The hook panel renders `cpu_ms`; `duration_ms` is diagnostic detail at most. Neither is the firing's wall cost, and the panel says so.
- A row with an empty session id or `hook.event` "unknown" indicates malformed stdin, kept for visibility rather than dropped.
- If the listener is down, hook rows are simply absent for that window — the same coverage-window honesty as every OTEL-fed metric.
- ADR-0001's amendment prevents the falsified "OTEL carries hook timings" sentence from justifying deletion of hook.py.
