#!/usr/bin/env python3
"""Hindsight self-instrumentation hook (ticket #23).

POSTs its own hook-event name and duration to the ingest listener as an
OTLP log record with event.name "hindsight.hook" — distinguishable by
name from Claude-emitted events, stored alongside them in otel_events.
The where-view's hook panel reads from there; OTEL provides no hook
telemetry of its own (falsified during definition — ADR-0005). If the
listener is down or slow the hook fails silently within a bounded
budget: every blocking leg (stdin wait, connect, response wait) is
individually capped at TIMEOUT, so the worst case is a small multiple
of it, never an unbounded stall — a hook must never slow or break a
session.

Installation is config, not code. Add to ~/.claude/settings.json (any
hook events you want timed; the script reads the event name from the
JSON Claude Code passes on stdin):

  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command":
      "python3 /path/to/hindsight/build/hook.py"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command":
      "python3 /path/to/hindsight/build/hook.py"}]}],
    "Stop": [{"hooks": [{"type": "command", "command":
      "python3 /path/to/hindsight/build/hook.py"}]}]
  }

Pass --port N if the listener is not on the default :4318.
"""
import json
import os
import resource
import select
import sys
import time
import urllib.request
from datetime import datetime, timezone

DEFAULT_PORT = 4318
# Seconds per blocking leg, NOT a total: the stdin wait, the connect, and
# the response wait are each bounded separately, so a pathological peer
# costs a small multiple of this (ADR-0005) — never an unbounded stall.
TIMEOUT = 0.5


def read_stdin(budget):
    """Bounded stdin read. Claude Code writes the hook JSON and closes;
    a stdin that never delivers EOF (hand-run from a terminal, a pipe
    left open) stops costing anything once the budget is spent."""
    fd, chunks = sys.stdin.fileno(), []
    deadline = time.monotonic() + budget
    while True:
        left = deadline - time.monotonic()
        if left <= 0 or not select.select([fd], [], [], left)[0]:
            break
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks).decode(errors="ignore")


def main(argv):
    start = time.perf_counter()
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else DEFAULT_PORT
    try:
        hook = json.loads(read_stdin(TIMEOUT))
    except Exception:
        hook = {}
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    # Two timings, neither the session's true cost of this firing (ADR-0005):
    # duration_ms is wall time of the script body only — its clock starts
    # after spawn + interpreter startup (tens of ms) and stops before the
    # POST, so it measures the instrument, not the session's cost. cpu_ms is
    # process CPU including interpreter startup — the per-firing cost figure
    # the hook panel charts. The true wall cost (spawn to exit, including
    # any timeout waits) is visible only to the spawning harness.
    ru = resource.getrusage(resource.RUSAGE_SELF)
    attrs = {
        "event.name": {"stringValue": "hindsight.hook"},
        "session.id": {"stringValue": hook.get("session_id") or ""},
        "event.timestamp": {"stringValue": ts},
        "hook.event": {"stringValue": hook.get("hook_event_name") or "unknown"},
        "hook.duration_ms": {"doubleValue": round((time.perf_counter() - start) * 1000, 3)},
        "hook.cpu_ms": {"doubleValue": round((ru.ru_utime + ru.ru_stime) * 1000, 3)},
    }
    payload = {"resourceLogs": [{"scopeLogs": [{"logRecords": [
        {"attributes": [{"key": k, "value": v} for k, v in attrs.items()]}]}]}]}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/logs", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    # The response body is discarded unread: urlopen has already consumed
    # the status line, and a .read() would add a second blocking wait on
    # the leg most likely to stall (the listener's SQLite write).
    urllib.request.urlopen(req, timeout=TIMEOUT).close()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        pass  # silent and fast: never surface an error into the session
