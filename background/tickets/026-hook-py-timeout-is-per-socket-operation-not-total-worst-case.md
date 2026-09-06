# #26 hook.py: TIMEOUT is per socket operation, not total — worst case ~2-3x the advertised bound

state: closed · labels: bug, needs-triage · opened: 2026-08-17 · closed: 2026-08-17

## Found by

Code review during ticket #24 (efficiency + simplification finders), verified against `build/hook.py`.

## Problem

`TIMEOUT = 0.5` is documented as the hard bound on what a dead or slow listener can cost a session, but urllib applies it per socket operation: connect, request write, and the response `.read()` each get their own 0.5s. A listener that is alive but slow (its SQLite write blocked behind a concurrent sync — `busy_timeout` is 5s) can cost ~1-1.5s per firing on the path the docstring promises is bounded at 0.5s.

The `.read()` at the end is pure waste: the response body is discarded, and it is the leg most likely to stall. `test_hung_listener_bounded_by_timeout`'s slack quietly stops describing reality.

## Acceptance criteria

- [ ] Drop the discarded `.read()`
- [ ] Either enforce a true total deadline or correct the comment/docstring to state the real worst case
- [ ] The hung-listener test asserts the documented bound



---

**comment · 2026-08-17**

Fixed in b911545. See the commit message and ADR-0005 for the recorded decision.

