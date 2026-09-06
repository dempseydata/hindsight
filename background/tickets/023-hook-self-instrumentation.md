# #23 Hook self-instrumentation

state: closed · labels: ready-for-agent · opened: 2026-08-16 · closed: 2026-08-17

## Parent

#15

## What to build

The where-view's hook panel gets its data source (OTEL has none — falsified during schema verification): a hook that POSTs its own name and duration to the ingest listener, stored alongside OTEL events. If the listener is down the hook fails silently and fast — a hook must never slow or break a session.

## Acceptance criteria

- [ ] Hook fires on real sessions and its timing rows appear in the store
- [ ] With the listener down, the hook exits quickly and silently (bounded timeout, no error surfaced to the session)
- [ ] Hook events are distinguishable from Claude-emitted OTEL events in the store
- [ ] Installation is documented config, not code the operator must write

## Blocked by

- #16


---

**comment · 2026-08-17**

Implemented in 9950de9 (build/hook.py + build/test_hook.py, no listener changes — the hook rides the existing /v1/logs OTLP path). Verified: 4 seam tests (timing row lands in the store; listener down = silent exit 0 in <2s via ECONNREFUSED; hung listener bounded by the 0.5s read timeout; garbage stdin silent), plus a live smoke against the running listener — row in otel_events: event_name hindsight.hook (distinguishable by name from Claude-emitted events), hook.event, hook.duration_ms 1.5, hook.cpu_ms 106.0 (CPU since spawn, including interpreter startup — the honest cost figure; self-measured wall time alone was misleading, caught in review). CONTEXT.md carries the new vocabulary.

One step remains before closing, and it is deliberately yours: pasting the hooks snippet (in build/hook.py's docstring) into ~/.claude/settings.json — installation is documented config, and which events to time (SessionStart / UserPromptSubmit / Stop suggested; Pre/PostToolUse cost a python spawn per tool call) is an operator choice I won't make in your global settings unasked.


---

**comment · 2026-08-17**

All acceptance criteria now verified. Installed 2026-08-17 in ~/.claude/settings.json on SessionStart / UserPromptSubmit / Stop (5s harness timeout atop the script's 0.5s internal bound). Hook fires on real sessions: 20 hindsight.hook rows in otel_events across 4 genuine session ids within hours of install, all three events represented, hook.cpu_ms 60-90ms per firing. Listener-down silence, bounded timeout, and distinguishability were verified at the seam in 9950de9's tests; installation is config only — no operator code.

