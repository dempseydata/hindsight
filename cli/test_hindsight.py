"""Seam tests for `/hindsight:ops` (ticket #83, ADR-0036): `hindsight.main(argv)`
with a temp HOME (so Hindsight home and ~/Library/LaunchAgents are temp too)
and stub `launchctl` / `open` executables on PATH that record their argv.
Asserts on what the operator can observe: files, the symlink, stdout, the
exit code and the launchctl calls."""
import contextlib
import io
import json
import os
import plistlib
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import hindsight

ROOT = Path(__file__).resolve().parent.parent
STUB = '#!/bin/sh\necho "$(basename "$0") $*" >> "$STUB_LOG"\n'


class OpsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.user = self.tmp / "user"
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        for name in ("launchctl", "open"):
            (bin_ / name).write_text(STUB)
            (bin_ / name).chmod(0o755)
        self.calls_file = self.tmp / "calls"
        env = {k: v for k, v in os.environ.items()
               if k not in ("HINDSIGHT_HOME", "HINDSIGHT_TZ", "HINDSIGHT_RAW_DAYS",
                             "CLAUDE_PLUGIN_DATA")}
        env.update(HOME=str(self.user), STUB_LOG=str(self.calls_file),
                   PATH=f"{bin_}:{os.environ['PATH']}")
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.home = self.user / ".hindsight"
        self.agents = self.user / "Library" / "LaunchAgents"

    def run_ops(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = hindsight.main(list(argv))
        return code or 0, out.getvalue()

    def calls(self):
        return self.calls_file.read_text().splitlines() if self.calls_file.exists() else []

    def plist(self, label):
        return plistlib.loads((self.agents / f"{label}.plist").read_bytes())

    # install

    def test_install_writes_both_jobs_against_current_with_this_interpreter(self):
        code, _ = self.run_ops("install")
        self.assertEqual(code, 0)
        self.assertEqual((self.home / "current").resolve(), ROOT)
        self.assertTrue((self.home / "logs").is_dir())
        ingest = self.plist("com.hindsight.ingest")
        self.assertEqual(ingest["ProgramArguments"],
                         [sys.executable, str(self.home / "current" / "cli" / "listener.py"), "--log"])
        self.assertTrue(ingest["KeepAlive"])
        nightly = self.plist("com.hindsight.nightly")
        self.assertEqual(nightly["ProgramArguments"],
                         [sys.executable, str(self.home / "current" / "cli" / "analyze.py"), "--log"])
        self.assertEqual(nightly["StartCalendarInterval"], {"Hour": 3, "Minute": 0})
        self.assertNotIn("KeepAlive", nightly)  # a scheduled invocation, not a daemon
        # launchd's default PATH lacks `claude`; the installing shell's is baked in
        self.assertEqual(nightly["EnvironmentVariables"]["PATH"], os.environ["PATH"])
        for p in (ingest, nightly):  # the job opens its own log, never launchd
            self.assertNotIn("StandardOutPath", p)
        domain = f"gui/{os.getuid()}"
        for label in ("com.hindsight.ingest", "com.hindsight.nightly"):
            self.assertIn(f"launchctl bootstrap {domain} {self.agents / (label + '.plist')}",
                          self.calls())

    def test_install_is_idempotent_and_replaces_v1_plists_in_place(self):
        self.agents.mkdir(parents=True)
        (self.agents / "com.hindsight.ingest.plist").write_text("v1")
        self.run_ops("install")
        first = {p.name: p.read_bytes() for p in self.agents.iterdir()}
        code, _ = self.run_ops("install")
        self.assertEqual(code, 0)
        self.assertEqual({p.name: p.read_bytes() for p in self.agents.iterdir()}, first)
        self.assertEqual(sorted(first), ["com.hindsight.ingest.plist",
                                         "com.hindsight.nightly.plist"])

    def test_install_bakes_the_pinned_environment_into_the_jobs(self):
        os.environ.update(HINDSIGHT_TZ="Asia/Tokyo", CLAUDE_PLUGIN_DATA=str(self.tmp / "data"),
                          HINDSIGHT_HOME=str(self.tmp / "elsewhere"))
        self.run_ops("install")
        env = self.plist("com.hindsight.nightly")["EnvironmentVariables"]
        self.assertEqual((env["HINDSIGHT_TZ"], env["CLAUDE_PLUGIN_DATA"], env["HINDSIGHT_HOME"]),
                         ("Asia/Tokyo", str(self.tmp / "data"), str(self.tmp / "elsewhere")))
        self.assertEqual(self.plist("com.hindsight.ingest")["EnvironmentVariables"]
                         ["HINDSIGHT_HOME"], str(self.tmp / "elsewhere"))
        self.assertTrue((self.tmp / "elsewhere" / "current").is_symlink())

    def test_install_bakes_the_raw_limit_into_the_nightly_only_when_set(self):
        self.run_ops("install")
        self.assertNotIn("HINDSIGHT_RAW_DAYS",
                         self.plist("com.hindsight.nightly")["EnvironmentVariables"])
        os.environ["HINDSIGHT_RAW_DAYS"] = "0"   # keep forever: a falsy-looking value still bakes
        self.run_ops("install")
        self.assertEqual(self.plist("com.hindsight.nightly")["EnvironmentVariables"]
                         ["HINDSIGHT_RAW_DAYS"], "0")

    def test_install_from_moves_a_v1_database_once_after_booting_out_the_jobs(self):
        v1 = self.tmp / "v1" / "hindsight.db"
        v1.parent.mkdir()
        v1.write_text("db")
        Path(f"{v1}-wal").write_text("wal")
        code, _ = self.run_ops("install", "--from", str(v1))
        self.assertEqual(code, 0)
        self.assertEqual((self.home / "hindsight.db").read_text(), "db")
        self.assertEqual((self.home / "hindsight.db-wal").read_text(), "wal")
        self.assertFalse(v1.exists())
        calls = self.calls()
        self.assertTrue(calls[0].startswith("launchctl bootout"), calls)
        self.assertTrue(calls[1].startswith("launchctl bootout"), calls)

    def test_install_from_refuses_when_a_database_is_already_there(self):
        self.home.mkdir(parents=True)
        (self.home / "hindsight.db").write_text("mine")
        v1 = self.tmp / "v1.db"
        v1.write_text("old")
        code, out = self.run_ops("install", "--from", str(v1))
        self.assertEqual(code, 1)
        self.assertIn("already", out)
        self.assertEqual((self.home / "hindsight.db").read_text(), "mine")
        self.assertTrue(v1.exists())
        self.assertEqual(self.calls(), [])

    def test_install_from_a_missing_path_refuses(self):
        code, out = self.run_ops("install", "--from", str(self.tmp / "nope.db"))
        self.assertEqual(code, 1)
        self.assertEqual(self.calls(), [])

    def test_install_prints_v1_hook_entries_and_never_edits_settings(self):
        settings = self.user / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        text = json.dumps({"hooks": {
            "Stop": [{"hooks": [{"type": "command",
                                 "command": "python3 /x/hindsight/build/hook.py"}]}],
            "PreToolUse": [{"hooks": [{"type": "command", "command": "other.sh"}]}]}})
        settings.write_text(text)
        _, out = self.run_ops("install")
        self.assertIn("Stop: python3 /x/hindsight/build/hook.py", out)
        self.assertNotIn("other.sh", out)
        self.assertEqual(settings.read_text(), text)

    # uninstall

    def test_uninstall_removes_jobs_and_current_but_never_the_database(self):
        self.run_ops("install")
        (self.home / "hindsight.db").write_text("history")
        code, out = self.run_ops("uninstall")
        self.assertEqual(code, 0)
        self.assertEqual(list(self.agents.iterdir()), [])
        self.assertFalse((self.home / "current").is_symlink())
        self.assertEqual((self.home / "hindsight.db").read_text(), "history")
        self.assertIn(f"rm -rf {self.home}", out)
        bootouts = [c for c in self.calls() if c.startswith("launchctl bootout")]
        self.assertTrue(any("com.hindsight.ingest" in c for c in bootouts[-2:]))
        self.assertTrue(any("com.hindsight.nightly" in c for c in bootouts[-2:]))

    # start / stop / serve / open

    def test_start_and_stop_control_the_listener(self):
        self.run_ops("install")
        self.calls_file.unlink()
        domain = f"gui/{os.getuid()}"
        self.assertEqual(self.run_ops("start")[0], 0)
        self.assertIn(f"launchctl bootstrap {domain} "
                      f"{self.agents / 'com.hindsight.ingest.plist'}", self.calls())
        self.calls_file.unlink()
        self.assertEqual(self.run_ops("stop")[0], 0)
        self.assertEqual(self.calls(), [f"launchctl bootout {domain}/com.hindsight.ingest"])

    def test_start_before_install_says_so(self):
        code, out = self.run_ops("start")
        self.assertEqual(code, 1)
        self.assertIn("/hindsight:ops install", out)

    def test_install_moves_v1_logs_into_home_without_overwriting(self):
        v1 = self.user / "Library" / "Logs" / "hindsight"
        v1.mkdir(parents=True)
        (v1 / "analyze.log").write_text("v1 history")
        (v1 / "listener.log").write_text("v1 listener")
        (self.home / "logs").mkdir(parents=True)
        (self.home / "logs" / "listener.log").write_text("newer")
        self.run_ops("install")
        self.assertEqual((self.home / "logs" / "analyze.log").read_text(), "v1 history")
        self.assertEqual((self.home / "logs" / "listener.log").read_text(), "newer")

    def test_install_warns_when_the_plugin_data_directory_is_unknown(self):
        self.assertIn("CLAUDE_PLUGIN_DATA is unset", self.run_ops("install")[1])
        os.environ["CLAUDE_PLUGIN_DATA"] = str(self.tmp / "data")
        self.assertNotIn("CLAUDE_PLUGIN_DATA is unset", self.run_ops("install")[1])

    def free_port(self):
        with socket.socket() as s:   # so a real server on :8321 is never hit
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def test_serve_starts_the_views_server_detached_logging_to_home(self):
        with mock.patch.object(hindsight, "SERVE_PORT", self.free_port()):
            code, out = self.run_ops("serve")
        self.assertEqual(code, 0)
        self.assertIn("starting", out)
        log = self.home / "logs" / "serve.log"
        for _ in range(40):   # no database here, so the server exits saying why
            if log.exists() and "no database" in log.read_text():
                break
            time.sleep(0.1)
        self.assertIn("no database", log.read_text())

    def test_serve_when_a_server_already_answers_starts_nothing(self):
        with mock.patch.object(hindsight, "http_up", return_value=True):
            code, out = self.run_ops("serve")
        self.assertEqual(code, 0)
        self.assertIn("already running", out)
        self.assertFalse((self.home / "logs" / "serve.log").exists())

    def test_open_with_no_database_reports_the_server_failure_and_opens_nothing(self):
        with mock.patch.object(hindsight, "SERVE_PORT", self.free_port()):
            code, out = self.run_ops("open")
        self.assertEqual(code, 1)
        self.assertIn("serve.log", out)
        self.assertIn("no database", (self.home / "logs" / "serve.log").read_text())
        self.assertFalse(any(c.startswith("open ") for c in self.calls()))

    def test_open_opens_the_what_view_when_the_server_answers(self):
        with mock.patch.object(hindsight, "http_up", return_value=True):
            self.assertEqual(self.run_ops("open")[0], 0)
        self.assertEqual(self.calls(), [f"open http://127.0.0.1:{hindsight.SERVE_PORT}/what"])

    def test_unknown_command_prints_usage(self):
        code, out = self.run_ops("bogus")
        self.assertEqual(code, 2)
        self.assertIn("install", out)


if __name__ == "__main__":
    unittest.main()
