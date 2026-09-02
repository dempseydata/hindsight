"""Tests for the self-instrumentation hook (ticket #23).

Seam: run hook.py as a subprocess with hook JSON on stdin — exactly how
Claude Code fires it — against an in-process listener on an ephemeral
port. Assert the store rows, and silence + speed when the listener is
down. No network beyond localhost.
"""
import json
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import listener

HOOK = Path(__file__).resolve().parent / "hook.py"

STDIN = {"session_id": "sess-hook", "transcript_path": "/tmp/x.jsonl",
         "hook_event_name": "PostToolUse", "tool_name": "Edit"}


def run_hook(port, stdin=json.dumps(STDIN)):
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(HOOK), "--port", str(port)],
        input=stdin.encode(), capture_output=True, timeout=10)
    return proc, time.perf_counter() - start


class HookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "test.db"
        cls.server = listener.make_server(port=0, db_path=cls.db)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def test_timing_row_appears_in_store(self):
        proc, _ = run_hook(self.port)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout + proc.stderr, b"")
        db = sqlite3.connect(self.db)
        row = db.execute(
            "SELECT event_name, session_id, timestamp, attributes FROM otel_events "
            "WHERE session_id='sess-hook'").fetchone()
        db.close()
        self.assertIsNotNone(row)
        # Distinguishable from Claude-emitted events by name.
        self.assertEqual(row[0], "hindsight.hook")
        self.assertTrue(row[2])
        attrs = json.loads(row[3])
        self.assertEqual(attrs["hook.event"], "PostToolUse")
        self.assertGreaterEqual(float(attrs["hook.duration_ms"]), 0)
        # cpu_ms includes interpreter startup, so it is never zero.
        self.assertGreater(float(attrs["hook.cpu_ms"]), 0)

    def test_listener_down_silent_and_fast(self):
        with socket.socket() as s:  # grab a port nothing listens on
            s.bind(("127.0.0.1", 0))
            dead_port = s.getsockname()[1]
        proc, elapsed = run_hook(dead_port)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout + proc.stderr, b"")
        self.assertLess(elapsed, 2)  # python spawn + instant refusal

    def test_hung_listener_bounded_by_timeout(self):
        # A listener that accepts but never responds: the read timeout,
        # not the connect refusal, is what bounds the hook here.
        with socket.socket() as hung:
            hung.bind(("127.0.0.1", 0))
            hung.listen(1)
            proc, elapsed = run_hook(hung.getsockname()[1])
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout + proc.stderr, b"")
        self.assertLess(elapsed, 2)  # spawn + 0.5s timeout, with slack

    def test_stdin_never_closed_bounded(self):
        # A stdin held open with no EOF (hand-run from a terminal, a pipe
        # the parent forgot to close) must not stall the hook.
        start = time.perf_counter()
        proc = subprocess.Popen(
            [sys.executable, str(HOOK), "--port", str(self.port)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("hook did not exit while stdin stayed open")
        finally:
            proc.stdin.close()
        self.assertEqual(proc.returncode, 0)
        self.assertLess(time.perf_counter() - start, 3)  # spawn + 0.5s budget

    def test_garbage_stdin_silent(self):
        proc, _ = run_hook(self.port, stdin="not json at all")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout + proc.stderr, b"")


if __name__ == "__main__":
    unittest.main()
