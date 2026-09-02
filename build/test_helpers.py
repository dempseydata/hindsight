"""Shared fixtures for the build/ seam tests (ticket #82): transcript
builders, canned model outputs, the replay stub and store-query helpers.

Imported by test_analyze, test_substrate, test_sunk_cost and
test_import_backfill. The TZ pin runs at import time: day buckets are the
operator's local day (ADR-0014), so fixtures need a pinned zone or they
assert whatever the runner's clock says.
"""
import json
import os
import sqlite3
import time

from substrate import LIVE_WINDOW_S

os.environ["TZ"] = "America/New_York"
time.tzset()

SKIP_MD = "SKIP"
REFUSAL_MD = ("I'm ready to generate audit-log entries, but I don't see a"
              " session transcript to analyze.")
ENTRY_A = "### Did a thing\n- **Did:** wrote a file"
ENTRY_B = "### Did another thing\n- **Did:** wrote a second file"
MERGED_ENTRY = "### Merged session\n- **Did:** wrote two files"

# Four-turn fixture conversation — also the extract content in
# test_import_backfill's fixtures.
FIXTURE_TURNS = [
    ("user", "we removed the openspec tool and switched to using to-spec instead for all specs"),
    ("assistant", "acknowledged, done"),
    ("user", "the migration to to-spec happened because openspec overlapped with existing tooling"),
    ("assistant", "noted"),
]


def write_transcript(path, turns, date="2026-08-01T10:00:00Z", version=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, (role, text) in enumerate(turns):
        entry = {"type": role, "uuid": f"{path.stem}-{i}", "timestamp": date}
        if version:
            entry["version"] = version
        entry["message"] = ({"content": text} if role == "user"
                             else {"content": [{"type": "text", "text": text}]})
        lines.append(json.dumps(entry))
    path.write_text("\n".join(lines) + "\n")
    _backdate(path)


def _backdate(path):
    """Fixture transcripts are finished sessions: age their mtime past the
    live-session guard (ticket #29). Live-guard tests re-touch to now."""
    t = time.time() - 2 * LIVE_WINDOW_S
    os.utime(path, (t, t))


def write_records(path, records):
    """Raw JSONL fixture — dicts are serialized, str items written verbatim
    (for malformed-line fixtures)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r)
                              for r in records) + "\n")
    _backdate(path)


def rec(role, uuid, ts, content, **msg):
    """One transcript record; extra kwargs (usage, model, id) land on the
    message object, as the CLI writes them."""
    return {"type": role, "uuid": uuid, "timestamp": ts,
            "message": {"content": content, **msg}}


USAGE = {"input_tokens": 10, "output_tokens": 20,
         "cache_creation_input_tokens": 30, "cache_read_input_tokens": 40}


def big_turns(n=140, size=2000):
    """Enough content to blow through the 180K chunk cap and force a
    multi-part extract."""
    turns = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        turns.append((role, f"turn {i} " + "x" * size))
    return turns


class StubRunner:
    """Replays canned model outputs in call order; an Exception instance in
    the queue is raised instead of returned. Records every prompt it saw."""

    def __init__(self, actions):
        self._it = iter(actions)
        self.calls = []

    def __call__(self, prompt):
        self.calls.append(prompt)
        action = next(self._it)
        if isinstance(action, Exception):
            raise action
        return action


class DbHelpers:
    """Store-query helpers over self.db — shared with test_import_backfill."""

    def rows(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        try:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql, params)]
        finally:
            conn.close()

    def audit_rows(self):
        return {r["session_id"]: r for r in self.rows("SELECT * FROM audit")}

    def session_statuses(self):
        conn = sqlite3.connect(self.db)
        try:
            return dict(conn.execute("SELECT id, status FROM sessions"))
        finally:
            conn.close()
