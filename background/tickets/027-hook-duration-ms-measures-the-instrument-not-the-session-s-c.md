# #27 hook.duration_ms measures the instrument, not the session's cost — and CONTEXT.md glosses it wrongly

state: closed · labels: bug, documentation, needs-triage · opened: 2026-08-17 · closed: 2026-08-17

## Found by

Code review during ticket #24 (cross-file tracer, measured end-to-end against a live listener), touching `build/hook.py` and CONTEXT.md's `hindsight.hook` bullet.

## Problem

`duration_ms` spans stdin parse to just before the POST — it excludes interpreter startup (tens of ms, not the "sub-ms" the docstring claims), the POST itself, and the process spawn. Measured: the hook reported `duration_ms=3.9` / `cpu_ms=88.7` while the session's real wall cost for that firing was ~299ms. Under a hung listener the TIMEOUT wait is invisible in both fields.

Consequence: the hook panel — the only data source for hook telemetry — exonerates the exact thing causing a slowdown. CONTEXT.md's gloss ("wall time the script can see: entry to just before the POST") starts the clock later than "entry" and frames a near-constant as the wall figure.

## Acceptance criteria

- [ ] Decide what the panel should chart: parent-side wall cost (e.g. spawn-to-exit measured by the harness slot) vs script-internal figures — and record the decision
- [ ] `cpu_ms`/`duration_ms` semantics stated accurately in hook.py and CONTEXT.md, including what neither can see
- [ ] The hook panel's presentation (ticket #15 tree) does not present `duration_ms` as the session's cost



---

**comment · 2026-08-17**

Fixed in b911545. See the commit message and ADR-0005 for the recorded decision.

