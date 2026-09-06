# #28 ADR-0001 still claims OTEL carries hook timings — falsified by the definition phase

state: closed · labels: documentation, needs-triage · opened: 2026-08-17 · closed: 2026-08-17

## Found by

Code review during ticket #24 (conventions finder).

## Problem

`docs/adr/0001-ingest-listener-not-strict-no-daemon.md` states "OTEL uniquely carries edit decisions, hook timings, api-error detail…". The definition phase falsified the hook-timings claim (`definition/ingest-schema-verification.md`: "Hook execution timings | **Falsified.**"), which is why `build/hook.py` self-instrumentation exists (ticket #23) and why CONTEXT.md now says "OTEL emits no hook telemetry".

CLAUDE.md directs `diagnosing-bugs` / `improve-codebase-architecture` to read CONTEXT.md + docs/adr/ first, so a future session reading ADR-0001 could delete hook.py as redundant — emptying the hook panel permanently with no error.

Related: the hook self-instrumentation decision (a new always-fires process, 0.5s bound, silent failure) has no ADR of its own; its rationale lives only in a module docstring and CONTEXT.md.

## Acceptance criteria

- [ ] ADR-0001 amended (an addendum note, not a rewrite of history) pointing at the falsification and hook.py
- [ ] The hook self-instrumentation decision recorded under docs/adr/



---

**comment · 2026-08-17**

Fixed in b911545. See the commit message and ADR-0005 for the recorded decision.

