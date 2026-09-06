# #25 hook.py: unbounded stdin.read() can stall a session despite the bounded-timeout contract

state: closed · labels: bug, needs-triage · opened: 2026-08-17 · closed: 2026-08-17

## Found by

Code review during ticket #24 (cross-file tracer + line-by-line finders), verified against `build/hook.py`.

## Problem

`sys.stdin.read()` is the first blocking call in `main()` and sits outside anything `TIMEOUT` covers — the 0.5s bound only applies to the urlopen socket operations. If the hook is ever spawned with stdin inherited from a terminal or an open pipe the parent has not closed (a user testing the docstring's command by hand, or any spawn path that doesn't write-and-close stdin), `read()` blocks forever and the session stalls on the one component whose design premise is that it cannot.

`test_hook.py` always passes a fully-written, closed stdin via `subprocess.run(input=...)`, so no test exercises the open-stdin case.

## Acceptance criteria

- [ ] A hook invocation whose stdin never closes exits within a bounded time (e.g. `select` with a deadline, or bounded read)
- [ ] A test covers the open-stdin case


---

**comment · 2026-08-17**

Fixed in b911545. See the commit message and ADR-0005 for the recorded decision.

