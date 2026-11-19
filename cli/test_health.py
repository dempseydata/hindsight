"""Seam tests for the SessionStart health check (ticket #93, ADR-0036 §6):
`health.main(argv)` with a SessionStart payload on stdin, a temp Hindsight
home and a stub `launchctl` on PATH that records its argv and answers with
$STUB_RC. Asserts on what the operator sees (stdout) and on `current`."""
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import health
import listener
from analyze import init_db
from test_helpers import run_hook

STUB = '#!/bin/sh\necho "$*" >> "$STUB_LOG"\nexit "${STUB_RC:-0}"\n'
NOW = datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


class HealthCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """One migrated store, copied per test: the migration is the cost."""
        cls.tmp = tempfile.TemporaryDirectory()
        cls.template = Path(cls.tmp.name) / "hindsight.db"
        init_db(cls.template).close()
        listener.init_db(cls.template)  # otel_events is the listener's

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        bin_ = base / "bin"
        bin_.mkdir()
        (bin_ / "launchctl").write_text(STUB)
        (bin_ / "launchctl").chmod(0o755)
        self.calls_file = base / "calls"
        self.home = base / "home"
        self.root = base / "plugin" / "0.2.0"
        self.root.mkdir(parents=True)
        self.env = {"HINDSIGHT_HOME": str(self.home), "CLAUDE_PLUGIN_ROOT": str(self.root),
                    "STUB_LOG": str(self.calls_file), "STUB_RC": "0",
                    "PATH": f"{bin_}:{os.environ['PATH']}"}

    def install(self):
        """What `/hindsight:ops install` leaves: the store, `current` at this
        plugin root, and (the stub's default) both jobs loaded."""
        self.home.mkdir()
        shutil.copy(self.template, self.home / "hindsight.db")
        (self.home / "current").symlink_to(self.root)

    def sql(self, sql, params=()):
        conn = sqlite3.connect(self.home / "hindsight.db")
        with conn:
            conn.execute(sql, params)
        conn.close()

    def health_row(self, source, success=None, failing_since=None):
        self.sql("INSERT OR REPLACE INTO health (source, last_success, last_error,"
                 " error_text, failing_since) VALUES (?, ?, ?, ?, ?)",
                 (source, success and iso(success), failing_since and iso(failing_since),
                  failing_since and "boom", failing_since and iso(failing_since)))

    def otel_stop(self, session, at):
        self.sql("INSERT INTO otel_events (event_name, session_id, timestamp, attributes)"
                 " VALUES ('hook_execution_complete', ?, ?, ?)",
                 (session, iso(at), json.dumps({"hook_event": "Stop"})))

    def captured(self, session, at):
        self.sql("INSERT INTO raw_records (session_id, byte_offset, line, captured_at)"
                 " VALUES (?, 0, x'00', ?)", (session, iso(at)))

    def check(self, session="current-sess"):
        out, err = run_hook(health.main, json.dumps(
            {"hook_event_name": "SessionStart", "session_id": session}), self.env)
        self.assertEqual(err, "")
        return out

    def message(self, out):
        self.assertEqual(out.count("\n"), 1, out)  # exactly one line
        body = json.loads(out)
        self.assertEqual(list(body), ["systemMessage"])  # never additionalContext
        return body["systemMessage"]

    def calls(self):
        return self.calls_file.read_text().splitlines() if self.calls_file.exists() else []

    def test_healthy_is_silent(self):
        self.install()
        for source in ("listener", "capture", "analysis"):
            self.health_row(source, success=NOW)
        self.otel_stop("a", NOW - timedelta(minutes=5))
        self.captured("a", NOW - timedelta(minutes=5) + timedelta(seconds=1))
        # the session starting now is not judged: its capture has not run yet
        self.otel_stop("current-sess", NOW)
        self.assertEqual(self.check(), "")
        self.assertFalse(any("kickstart" in c for c in self.calls()))

    def test_capture_behind_otel_names_capture(self):
        self.install()
        self.captured("a", NOW - timedelta(hours=3))
        self.otel_stop("a", NOW - timedelta(hours=2))
        msg = self.message(self.check())
        self.assertIn("capture", msg)
        self.assertIn("2 hours", msg)  # since the first Stop capture missed

    def test_a_first_stop_still_being_captured_is_on_time(self):
        self.install()
        self.otel_stop("a", NOW - timedelta(seconds=10))  # no capture yet
        self.assertEqual(self.check(), "")

    def test_a_resumed_session_counts_from_its_first_missed_stop(self):
        self.install()
        self.captured("a", NOW - timedelta(days=7))
        self.otel_stop("a", NOW - timedelta(days=7))
        self.otel_stop("a", NOW - timedelta(hours=1))
        self.otel_stop("a", NOW - timedelta(minutes=30))
        msg = self.message(self.check())
        self.assertIn("capture behind OTel for 1 hour", msg)

    def test_timestamps_without_z_parse(self):
        self.install()
        self.health_row("analysis", success=NOW - timedelta(days=4))
        self.sql("UPDATE health SET failing_since=? WHERE source='analysis'",
                 ((NOW - timedelta(days=3, hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),))
        msg = self.message(self.check())
        self.assertIn("analysis failing for 3 days", msg)

    def test_a_directory_at_current_is_reported_and_kept(self):
        self.install()
        (self.home / "current").unlink()
        (self.home / "current").mkdir()
        msg = self.message(self.check())
        self.assertNotIn("failed", msg)
        self.assertNotIn(str(self.home), msg)
        self.assertIn("`current`", msg)
        self.assertTrue((self.home / "current").is_dir())
        self.assertFalse((self.home / "current").is_symlink())
        self.assertFalse(any("kickstart" in c for c in self.calls()))
        self.assertEqual(list(self.home.glob("current.*")), [])  # no stray temp link

    def test_a_session_otel_saw_and_capture_never_did_names_capture(self):
        self.install()
        self.otel_stop("a", NOW - timedelta(days=2))
        self.assertIn("capture", self.message(self.check()))

    def test_a_compacted_session_is_not_behind(self):
        self.install()
        self.sql("INSERT INTO transcripts (session_id, path, high_water)"
                 " VALUES ('a', 'a.jsonl', 10)")  # raw records gone, high-water kept
        self.otel_stop("a", NOW - timedelta(days=40))
        self.assertEqual(self.check(), "")

    def test_a_failing_analysis_row_gives_its_age_in_days(self):
        self.install()
        self.health_row("analysis", success=NOW - timedelta(days=4),
                        failing_since=NOW - timedelta(days=3, hours=1))
        msg = self.message(self.check())
        self.assertIn("analysis", msg)
        self.assertIn("3 days", msg)

    def test_no_database_is_not_installed_without_raising(self):
        msg = self.message(self.check())
        self.assertIn("not installed — run `/hindsight:ops install`", msg)
        self.assertFalse(self.home.exists())  # the check creates nothing

    def test_jobs_not_loaded_is_not_installed(self):
        self.install()
        self.env["STUB_RC"] = "113"  # launchctl print: no such service
        msg = self.message(self.check())
        self.assertIn("not installed — run `/hindsight:ops install`", msg)
        self.assertIn(f"print gui/{os.getuid()}/com.hindsight.ingest", self.calls())

    def test_no_launchctl_is_not_installed_without_raising(self):
        self.install()
        self.env["PATH"] = str(self.root)  # no launchctl anywhere
        self.assertIn("not installed", self.message(self.check()))

    def test_a_differing_current_is_repointed_and_the_listener_kickstarted(self):
        self.install()
        old = self.root.parent / "0.1.0"
        old.mkdir()
        (self.home / "current").unlink()
        (self.home / "current").symlink_to(old)
        self.assertEqual(self.check(), "")
        self.assertEqual((self.home / "current").resolve(), self.root.resolve())
        self.assertIn(f"kickstart -k gui/{os.getuid()}/com.hindsight.ingest", self.calls())

    def test_registered_synchronous_on_session_start(self):
        hooks = json.loads((Path(health.__file__).resolve().parent.parent
                            / "hooks" / "hooks.json").read_text())["hooks"]
        entries = [h for g in hooks["SessionStart"] for h in g["hooks"]
                   if "cli/health.py" in h["command"]]
        self.assertEqual(len(entries), 1)
        self.assertNotIn("async", entries[0])
        self.assertNotIn("health.py", json.dumps({k: v for k, v in hooks.items()
                                                   if k != "SessionStart"}))


if __name__ == "__main__":
    unittest.main()
