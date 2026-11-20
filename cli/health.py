#!/usr/bin/env python3
"""The health check (ticket #93, ADR-0036 §6, ADR-0033 §6).

A synchronous SessionStart hook, budgeted at about 100 ms. Silent when
collection is healthy: plain stdout would land in the model's context.
Otherwise one JSON `systemMessage` line, shown to the operator only:

- not installed (no database, or either launchd job not loaded);
- a source failing, for how long since the first error of the unbroken run;
- capture behind OTel: OTel saw a `Stop` for a session (not the one now
  starting) more recently than capture captured anything for it.

When `current` does not resolve to ${CLAUDE_PLUGIN_ROOT} it is re-pointed
and the listener kickstarted, so a plugin update takes effect here. Reads
the store read-only, never migrates it, and never raises. Held sessions are
a designed skip and stay silent (ADR-0039 §5).
"""
import json
import os
import select
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote  # not Path.as_uri: it imports urllib.request, ~60 ms

sys.path.insert(0, str(Path(__file__).resolve().parent))
from home import INGEST, NIGHTLY, domain, home  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent  # the plugin root, if the env has none
TIMEOUT = 0.05  # stdin: the payload is already written when the hook starts
# shortcut: capture runs detached on the Stop that OTel reports, so a capture
# a few seconds after the OTel event is on time; widen if it ever false-trips.
GRACE_S = 120
NOT_INSTALLED = "not installed — run `/hindsight:ops install`"


def launchctl(*args):
    try:
        return subprocess.run(["launchctl", *args], capture_output=True, timeout=1).returncode
    except (OSError, subprocess.SubprocessError):
        return None


def parse(ts):
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # stored UTC, Z or not


def ago(ts, now):
    s = (now - (parse(ts) if isinstance(ts, str) else ts)).total_seconds()
    n, unit = ((int(s // 86400), "day") if s >= 86400 else
               (int(s // 3600), "hour") if s >= 3600 else (max(int(s // 60), 1), "minute"))
    return f"{n} {unit}{'s' if n != 1 else ''}"


def repoint(root):
    current = home() / "current"
    if current.is_dir() and not current.is_symlink():  # the operator's; never delete it
        return ["`current` in Hindsight home is a directory, not a link — move it aside"]
    if current.resolve() == root.resolve():
        return []
    tmp = current.with_name(f"current.{os.getpid()}")
    tmp.unlink(missing_ok=True)
    tmp.symlink_to(root)
    os.replace(tmp, current)  # atomic: a concurrent SessionStart sees old or new
    launchctl("kickstart", "-k", f"{domain()}/{INGEST}")
    return []


def problems(conn, session, now):
    out = [f"{source} failing for {ago(since, now)}" for source, since in conn.execute(
        "SELECT source, failing_since FROM health"
        " WHERE failing_since IS NOT NULL ORDER BY source")]
    try:
        return out + capture_behind(conn, session, now)
    except sqlite3.OperationalError:
        return out  # no otel_events: the listener has never opened the store


def capture_behind(conn, session, now):
    # newest OTel Stop of another session; rowid order keeps this off a full scan
    stop = conn.execute(
        "SELECT session_id, timestamp FROM otel_events WHERE event_name="
        "'hook_execution_complete' AND json_extract(attributes, '$.hook_event')='Stop'"
        " AND session_id IS NOT NULL AND session_id IS NOT ? AND timestamp IS NOT NULL"
        " ORDER BY id DESC LIMIT 1", (session,)).fetchone()
    if not stop:
        return []
    sid = stop[0]
    (captured,) = conn.execute("SELECT max(captured_at) FROM raw_records"
                               " WHERE session_id=?", (sid,)).fetchone()
    if not captured and conn.execute(
            "SELECT 1 FROM transcripts WHERE session_id=? AND high_water > 0",
            (sid,)).fetchone():
        return []  # compacted: raw records gone, high-water kept
    # a Stop within the grace of the last capture is the one it captured
    after = parse(captured) + timedelta(seconds=GRACE_S) if captured else None
    missed = [t for t in (parse(ts) for (ts,) in conn.execute(
        "SELECT timestamp FROM otel_events WHERE session_id=? AND event_name="
        "'hook_execution_complete' AND json_extract(attributes, '$.hook_event')='Stop'"
        " AND timestamp IS NOT NULL", (sid,))) if after is None or t > after]
    first = min(missed, default=None)
    if first and (now - first).total_seconds() > GRACE_S:
        return [f"capture behind OTel for {ago(first, now)} (session {sid[:8]})"]
    return []


def check(session):
    db = home() / "hindsight.db"
    if not db.is_file() or any(launchctl("print", f"{domain()}/{label}") != 0
                               for label in (INGEST, NIGHTLY)):
        return [NOT_INSTALLED]
    out = repoint(Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or ROOT))
    conn = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True, timeout=1)
    try:
        return out + problems(conn, session, datetime.now(timezone.utc))
    except sqlite3.OperationalError:
        return out  # a store not yet migrated to v10 has no health to judge
    finally:
        conn.close()


def read_session():
    """The starting session's id. One bounded read: the payload is small and
    already written; missing or partial, no session is excluded."""
    try:
        fd = sys.stdin.fileno()
        hook = json.loads(os.read(fd, 65536)) if select.select([fd], [], [], TIMEOUT)[0] else {}
    except (OSError, ValueError):
        return None
    return hook.get("session_id") if isinstance(hook, dict) else None


def main(argv):
    try:
        lines = check(read_session())
    except Exception as e:  # never raise into the session; say so instead
        lines = [f"health check failed: {type(e).__name__}: {e}"]
    if lines:
        print(json.dumps({"systemMessage": "hindsight: " + "; ".join(lines)},
                         ensure_ascii=False))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        pass
