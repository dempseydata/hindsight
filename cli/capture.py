#!/usr/bin/env python3
"""The capture hook (ticket #84, ADR-0031, ADR-0033 §1-2).

Registered `"async": true` by hooks/hooks.json on SessionStart, Stop and
SubagentStop, so Claude Code runs it detached and the turn never waits.

- Stop: capture `transcript_path` from its high-water.
- SubagentStop: capture `agent_transcript_path` under the parent session
  with its agent id, and the parent too.
- SessionStart: record the folder identity (the inode of `cwd`, ADR-0018)
  on the session's registry row, where the analysis run's identity fill
  reads it.

Capture verifies the hash of the last captured line, then stores every
complete line past the high-water verbatim (trailing newline included),
zlib-compressed one by one, and advances the high-water — one transaction.
It never parses JSON. A mismatch is a breakage and nothing is appended.
The session and agent come from the transcript path, never from the
payload's ids (ADR-0039 §4). The `sweep` (#86) runs `capture` too.

Writes the `capture` health row. Never raises into the session.
"""
import hashlib
import json
import os
import select
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from home import home  # noqa: E402

TIMEOUT = 0.5  # the stdin wait: a pipe left open must not hold the process
REWRITTEN = 6  # breakage condition: a captured prefix no longer matches
EVENTS = ("SessionStart", "Stop", "SubagentStop")  # as registered in hooks/hooks.json


def is_transcript(path):
    return isinstance(path, str) and path.endswith(".jsonl")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_stdin(budget):
    """Bounded stdin read: Claude Code writes the payload and closes; a
    stdin that never delivers EOF stops costing anything after `budget`."""
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


def transcript_key(path):
    """(session, agent) from a transcript path (ADR-0039 §4):
    `<session>.jsonl` is the parent (agent None);
    `<session>/subagents/agent-<id>.jsonl` is a subagent of <session>."""
    p = Path(path)
    if p.parent.name == "subagents" and p.stem.startswith("agent-"):
        return p.parent.parent.name, p.stem.removeprefix("agent-")
    return p.stem, None


def _registry(conn, sid, aid):
    return conn.execute(
        "SELECT high_water, last_hash, last_size FROM transcripts"
        " WHERE session_id=? AND agent_id IS ?", (sid, aid)).fetchone()


def _upsert_registry(conn, sid, aid, path, **cols):
    sets = ", ".join(f"{k}=?" for k in cols)
    if not conn.execute(f"UPDATE transcripts SET path=?, {sets}"
                        " WHERE session_id=? AND agent_id IS ?",
                        (path, *cols.values(), sid, aid)).rowcount:
        conn.execute(f"INSERT INTO transcripts (session_id, agent_id, path,"
                     f" {', '.join(cols)}) VALUES (?, ?, ?{', ?' * len(cols)})",
                     (sid, aid, path, *cols.values()))


def capture(conn, path):
    """Append `path`'s complete lines past its high-water to the raw store.
    Returns the count of lines stored. The write lock is taken first, so two
    firings over one transcript serialise instead of racing the high-water."""
    sid, aid = transcript_key(path)
    path = str(path)
    conn.execute("BEGIN IMMEDIATE")
    try:
        reg = _registry(conn, sid, aid)
        hw, last_hash, last_size = reg if reg else (0, None, None)
        with open(path, "rb") as f:
            if last_size:
                f.seek(hw - last_size)
                if hashlib.sha256(f.read(last_size)).hexdigest() != last_hash:
                    _rewritten(conn, sid)
                    conn.commit()
                    return 0
            f.seek(hw)
            tail = f.read()
        tail = tail[:tail.rfind(b"\n") + 1]  # a trailing partial line waits
        lines = [ln + b"\n" for ln in tail.split(b"\n")[:-1]]  # \n only, never \r
        at, offset = now(), hw
        for line in lines:
            conn.execute("INSERT OR IGNORE INTO raw_records (session_id, agent_id,"
                         " byte_offset, line, captured_at) VALUES (?, ?, ?, ?, ?)",
                         (sid, aid, offset, zlib.compress(line), at))
            offset += len(line)
        if lines:
            _upsert_registry(conn, sid, aid, path, high_water=offset,
                             last_hash=hashlib.sha256(lines[-1]).hexdigest(),
                             last_size=len(lines[-1]))
        conn.commit()
        return len(lines)
    except BaseException:
        conn.rollback()
        raise


def _rewritten(conn, sid):
    """One open breakage row per rewritten session, not one per firing."""
    if not conn.execute("SELECT 1 FROM breakage WHERE acknowledged_at IS NULL"
                        " AND condition=? AND session_id=?",
                        (REWRITTEN, sid)).fetchone():
        conn.execute("INSERT INTO breakage (at, tier, condition, source, session_id)"
                     " VALUES (?, 'problem', ?, 'capture', ?)", (now(), REWRITTEN, sid))


def record_identity(conn, transcript_path, cwd):
    """The folder identity at SessionStart (ADR-0018), on the session's
    registry row. A missing or unreadable cwd records nothing: identity is a
    recorded fact or absent, never guessed. A later SessionStart (a resume)
    never overwrites the first identity recorded."""
    try:
        fid = os.stat(cwd).st_ino
    except (OSError, TypeError, ValueError):
        return
    sid, aid = transcript_key(transcript_path)
    conn.execute("BEGIN IMMEDIATE")
    if not conn.execute("UPDATE transcripts SET folder_identity ="
                        " ifnull(folder_identity, ?) WHERE session_id=?"
                        " AND agent_id IS ?", (fid, sid, aid)).rowcount:
        conn.execute("INSERT INTO transcripts (session_id, agent_id, path,"
                     " folder_identity) VALUES (?, ?, ?, ?)",
                     (sid, aid, str(transcript_path), fid))
    conn.commit()


def write_health(conn, error=None, source="capture"):
    """A source's health row (ADR-0039 §5): failing_since is set by the
    first error after a success and cleared by the next success."""
    at = now()
    conn.execute("INSERT OR IGNORE INTO health (source) VALUES (?)", (source,))
    if error is None:
        conn.execute("UPDATE health SET last_success=?, failing_since=NULL"
                     " WHERE source=?", (at, source))
    else:
        conn.execute("UPDATE health SET last_error=?, error_text=?,"
                     " failing_since=ifnull(failing_since, ?) WHERE source=?",
                     (at, error, at, source))
    conn.commit()


def handle(conn, hook):
    event = hook.get("hook_event_name")
    if event == "SessionStart":
        record_identity(conn, hook["transcript_path"], hook.get("cwd"))
    elif event == "Stop":
        capture(conn, hook["transcript_path"])
    elif event == "SubagentStop":
        for key in ("agent_transcript_path", "transcript_path"):
            if is_transcript(hook.get(key)):
                try:
                    capture(conn, hook[key])
                except FileNotFoundError:
                    pass  # a missing file is skipped; the other is still captured


def main(argv):
    try:
        hook = json.loads(read_stdin(TIMEOUT))
    except ValueError:
        return
    if (not isinstance(hook, dict) or hook.get("hook_event_name") not in EVENTS
            or not is_transcript(hook.get("transcript_path"))):
        return  # not ours, or nothing named to capture: not collection's failure
    from analyze import init_db  # the schema's owner; deferred past the cheap exits
    conn = init_db(home() / "hindsight.db")
    try:
        try:
            handle(conn, hook)
        except Exception as e:
            conn.rollback()
            write_health(conn, f"{hook.get('hook_event_name')}: {type(e).__name__}: {e}")
        else:
            write_health(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        pass  # never surface an error into the session
