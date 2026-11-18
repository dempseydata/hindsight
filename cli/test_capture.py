"""Tests for the capture hook (ticket #84, ADR-0031, ADR-0033 §1-2).

Seam: run capture.py as a subprocess with hook JSON on stdin and a temp
Hindsight home — exactly how Claude Code fires it. Assert the store: raw
records, the breakage table, the capture health row. Detaching (the
hooks.json `async` flag) is Claude Code's, not tested here.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "capture.py"

L1 = b'{"type":"user","n":1}\n'
L2 = b'{"type":"assistant","n":2}\n'
L3 = b'{"type":"user","n":3}\n'


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.db = self.home / "hindsight.db"
        self.proj = base / "projects" / "proj"
        self.proj.mkdir(parents=True)
        self.parent = self.proj / "sess-1.jsonl"

    def fire(self, payload):
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        proc = subprocess.run(
            [sys.executable, str(CAPTURE)], input=stdin.encode(),
            capture_output=True, timeout=30,
            env={**os.environ, "HINDSIGHT_HOME": str(self.home)})
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout + proc.stderr, b"")
        return proc

    def stop(self, path=None):
        return self.fire({"session_id": "sess-1", "hook_event_name": "Stop",
                          "transcript_path": str(path or self.parent)})

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def records(self, agent=None):
        """The stored lines of one transcript, in offset order."""
        return [zlib.decompress(b) for (b,) in self.query(
            "SELECT line FROM raw_records WHERE session_id='sess-1'"
            " AND agent_id IS ? ORDER BY byte_offset", (agent,))]

    def health(self):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            r = conn.execute("SELECT * FROM health WHERE source='capture'").fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def test_stop_captures_from_the_high_water_and_leaves_a_partial_line(self):
        self.parent.write_bytes(L1 + L2)
        self.stop()
        self.assertEqual(self.records(), [L1, L2])

        with self.parent.open("ab") as f:
            f.write(L3 + b'{"type":"assist')  # a line still being written
        self.stop()
        self.assertEqual(self.records(), [L1, L2, L3])
        # the stored records in offset order rebuild the file's prefix
        self.assertEqual(b"".join(self.records()), L1 + L2 + L3)

        self.stop()  # a repeat firing adds nothing
        self.assertEqual(len(self.records()), 3)

        with self.parent.open("ab") as f:
            f.write(b'ant"}\n')  # the partial line completes
        self.stop()
        self.assertEqual(self.records(), [L1, L2, L3, b'{"type":"assistant"}\n'])
        self.assertEqual(b"".join(self.records()), self.parent.read_bytes())

    def test_a_rewritten_prefix_is_a_breakage_and_appends_nothing(self):
        self.parent.write_bytes(L1 + L2)
        self.stop()
        self.parent.write_bytes(L1 + b'{"type":"assistant","n":9}\n' + L3)
        self.stop()
        self.assertEqual(self.records(), [L1, L2])
        rows = self.query("SELECT tier, source, session_id FROM breakage"
                          " WHERE acknowledged_at IS NULL")
        self.assertEqual(rows, [("problem", "capture", "sess-1")])
        self.stop()  # still rewritten: the open row is not repeated
        self.assertEqual(len(self.query("SELECT 1 FROM breakage")), 1)

    def test_a_truncated_transcript_is_a_breakage(self):
        self.parent.write_bytes(L1 + L2)
        self.stop()
        self.parent.write_bytes(L1)
        self.stop()
        self.assertEqual(self.records(), [L1, L2])
        self.assertEqual(len(self.query("SELECT 1 FROM breakage")), 1)

    def test_subagent_stop_files_under_the_parent_with_its_agent_id(self):
        sub = self.proj / "sess-1" / "subagents" / "agent-a1b2.jsonl"
        sub.parent.mkdir(parents=True)
        sub.write_bytes(L3)
        self.parent.write_bytes(L1 + L2)
        # payload ids disagree with the path on purpose: the path is the key
        self.fire({"session_id": "other", "agent_id": "zzz",
                   "hook_event_name": "SubagentStop",
                   "transcript_path": str(self.parent),
                   "agent_transcript_path": str(sub)})
        self.assertEqual(self.records("a1b2"), [L3])
        self.assertEqual(self.records(), [L1, L2])
        self.assertEqual(self.query("SELECT DISTINCT session_id FROM raw_records"),
                         [("sess-1",)])

    def test_health_records_last_success_then_last_error_with_its_text(self):
        self.parent.write_bytes(L1)
        self.stop()
        h = self.health()
        self.assertTrue(h["last_success"].endswith("Z"))
        self.assertIsNone(h["last_error"])

        self.stop(self.proj / "gone.jsonl")
        h = self.health()
        self.assertTrue(h["last_error"].endswith("Z"))
        self.assertIn("gone.jsonl", h["error_text"])
        self.assertEqual(h["failing_since"], h["last_error"])

        self.stop()
        h = self.health()
        self.assertIsNone(h["failing_since"])
        self.assertIsNotNone(h["last_error"])  # history kept, failure cleared

    def test_captured_at_is_iso_utc(self):
        self.parent.write_bytes(L1)
        self.stop()
        (at,) = self.query("SELECT captured_at FROM raw_records")[0]
        self.assertRegex(at, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z$")

    def test_malformed_or_empty_payloads_never_raise(self):
        for stdin in ("", "not json at all", "[1, 2]", "null",
                      json.dumps({"hook_event_name": "Stop"}),
                      json.dumps({"hook_event_name": "SubagentStop",
                                  "transcript_path": 7}),
                      json.dumps({"hook_event_name": "SessionStart",
                                  "transcript_path": str(self.parent),
                                  "cwd": "/no/such/dir"})):
            with self.subTest(stdin=stdin):
                self.fire(stdin)

    def test_a_bare_carriage_return_does_not_split_a_record(self):
        line = b'{"x":"a\rb"}\n'  # ADR-0039 §3: a record runs through \n
        self.parent.write_bytes(line + L1)
        self.stop()
        self.assertEqual(self.records(), [line, L1])

    def test_a_path_not_ending_jsonl_is_ignored(self):
        other = self.proj / "hosts"
        other.write_bytes(L1)
        self.stop(other)
        self.assertFalse(self.db.exists())

    def test_an_unregistered_event_touches_nothing(self):
        self.parent.write_bytes(L1)
        self.fire({"hook_event_name": "UserPromptSubmit",
                   "transcript_path": str(self.parent)})
        self.assertFalse(self.db.exists())

    def test_subagent_stop_with_a_missing_agent_file_still_captures_the_parent(self):
        self.parent.write_bytes(L1)
        self.fire({"hook_event_name": "SubagentStop",
                   "transcript_path": str(self.parent),
                   "agent_transcript_path": str(
                       self.proj / "sess-1" / "subagents" / "agent-gone.jsonl")})
        self.assertEqual(self.records(), [L1])

    def test_stdin_never_closed_bounded(self):
        start = time.perf_counter()
        proc = subprocess.Popen(
            [sys.executable, str(CAPTURE)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "HINDSIGHT_HOME": str(self.home)})
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("capture did not exit while stdin stayed open")
        finally:
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()
        self.assertEqual(proc.returncode, 0)
        self.assertLess(time.perf_counter() - start, 3)


class RegistrationTest(unittest.TestCase):
    """The plugin registers one async capture entry on the three events, and
    the v1 self-instrumentation hook is gone (ticket #84, ADR-0033 §7)."""

    def test_capture_registered_async_on_three_events_and_hook_py_gone(self):
        hooks = json.loads((HERE.parent / "hooks" / "hooks.json").read_text())["hooks"]
        for event in ("SessionStart", "Stop", "SubagentStop"):
            with self.subTest(event=event):
                entries = [h for g in hooks[event] for h in g["hooks"]]
                capture = [h for h in entries if "cli/capture.py" in h["command"]]
                self.assertEqual(len(capture), 1)
                self.assertIs(capture[0].get("async"), True)
        self.assertNotIn("hook.py", json.dumps(hooks))
        self.assertFalse((HERE / "hook.py").exists())


if __name__ == "__main__":
    unittest.main()
