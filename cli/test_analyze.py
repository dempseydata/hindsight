"""Seam-2 tests for the analysis-run entrypoint (ticket #17).

External behaviour of the entrypoint only: run it over a fixture transcript
directory with a stubbed model runner (no live model calls — the frozen
what-pass's own quality is the weekly spot-check's job, not this seam's)
and assert the `sessions`/`audit` rows it produces.

Substrate-scan and sunk-cost-scan seams live in test_substrate.py and
test_sunk_cost.py; shared fixtures in test_helpers.py (ticket #82).
"""
import hashlib
import contextlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

import analyze
from analyze import LimitExhausted, run_analysis
from sunk_cost import scan_sunk_cost as sunk_cost_scan
from test_helpers import (DbHelpers, ENTRY_A, ENTRY_B, FIXTURE_TURNS,
                          MERGED_ENTRY, REFUSAL_MD, SKIP_MD, StubRunner,
                          USAGE, _backdate, big_turns, captured_earlier,
                          fire_capture, rec, session_start, settle_captures,
                          write_records, write_transcript)



class AnalyzeTest(DbHelpers, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.proj = self.root / "test-project"

    def run_pipeline(self, model_runner, live=False):
        # Fixture backstop dirs (may not exist): the run must never touch
        # the real ~/.claude or project repos from a test.
        base = Path(self.tmp.name)
        with contextlib.nullcontext() if live else captured_earlier():
            run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                          model_runner=model_runner,
                          claude_dir=base / "claude", projects_dir=base / "repos")

    def test_trivial_session_skip_and_idempotent_second_run(self):
        write_transcript(self.proj / "sess-trivial.jsonl",
                          [("user", "fix the typo"), ("assistant", "done")])
        stub = StubRunner([SKIP_MD])
        self.run_pipeline(stub)

        rows = self.audit_rows()
        self.assertEqual(rows["sess-trivial"]["skip"], 1)
        self.assertIsNone(rows["sess-trivial"]["markdown"])
        self.assertEqual(self.session_statuses(), {"sess-trivial": "done"})

        # Second run: no new transcripts, session already done — a stub with
        # zero actions proves no model call happens (StopIteration if it did).
        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.audit_rows(), rows)

    def test_work_dir_owner_only_under_open_umask(self):
        # Extracts are transcript text: closed whatever the umask, even pre-existing.
        self.work.mkdir(mode=0o755)
        write_transcript(self.proj / "sess-modes.jsonl",
                          [("user", "fix the typo"), ("assistant", "done")])
        old = os.umask(0o022)
        try:
            self.run_pipeline(StubRunner([SKIP_MD]))
        finally:
            os.umask(old)
        self.assertEqual(self.work.stat().st_mode & 0o777, 0o700)

    def test_audit_rows_carry_prompt_version_and_model(self):
        write_transcript(self.proj / "sess-v.jsonl",
                          [("user", "ship the feature"), ("assistant", "shipped")])
        self.run_pipeline(StubRunner([ENTRY_A]))
        row = self.audit_rows()["sess-v"]
        self.assertEqual(row["prompt_version"], analyze.PROMPT_VERSION)
        self.assertEqual(row["model"], analyze.MODEL)
        self.assertEqual(row["markdown"], ENTRY_A)
        self.assertEqual(row["skip"], 0)

    def test_analysis_run_transcript_excluded_from_inventory(self):
        write_transcript(self.proj / "sess-self.jsonl",
                          [("user", "You are generating one audit-log entry for..."),
                           ("assistant", "### x")])
        write_transcript(self.proj / "sess-real.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])
        self.run_pipeline(StubRunner([ENTRY_A]))  # only sess-real should ever call the runner

        statuses = self.session_statuses()
        self.assertNotIn("sess-self", statuses)
        self.assertIn("sess-real", statuses)
        self.assertNotIn("sess-self", self.audit_rows())

        # The excluded id is remembered so later runs skip its head-scan
        # entirely instead of re-scanning every self-excluded transcript
        # forever (each analysis run mints new claude -p transcripts).
        conn = sqlite3.connect(self.db)
        try:
            excluded = [r[0] for r in conn.execute("SELECT id FROM excluded_sessions")]
        finally:
            conn.close()
        self.assertEqual(excluded, ["sess-self"])
        self.run_pipeline(StubRunner([]))  # second run: no calls, no re-insert crash

    def test_multipart_session_merges_into_one_audit_entry(self):
        write_transcript(self.proj / "sess-multi.jsonl", big_turns())
        stub = StubRunner([ENTRY_A, ENTRY_B, MERGED_ENTRY])
        self.run_pipeline(stub)

        parts = sorted((self.work / "extracts").glob("sess-multi.part*.txt"))
        self.assertGreaterEqual(len(parts), 2, "fixture must force a multi-part extract")

        rows = self.audit_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows["sess-multi"]["markdown"], MERGED_ENTRY)
        # one what-pass call per part + the merge call
        self.assertEqual(len(stub.calls), 3)

    def test_limit_exhaustion_pauses_then_next_run_resumes(self):
        write_transcript(self.proj / "sess-a.jsonl",
                          [("user", "task a"), ("assistant", "done a")])
        write_transcript(self.proj / "sess-b.jsonl",
                          [("user", "task b"), ("assistant", "done b")])
        write_transcript(self.proj / "sess-c.jsonl",
                          [("user", "task c"), ("assistant", "done c")])

        # Sorted processing order: a, b, c. a's what-pass call completes; b's
        # what-pass call hits the limit; c is never attempted (a
        # StopIteration would fail the test if it were).
        self.run_pipeline(StubRunner(
            [ENTRY_A, LimitExhausted("usage limit reached")]))

        statuses = self.session_statuses()
        self.assertEqual(statuses["sess-a"], "done")
        self.assertEqual(statuses["sess-b"], "pending")
        self.assertEqual(statuses["sess-c"], "pending")
        rows = self.audit_rows()
        self.assertIn("sess-a", rows)
        self.assertNotIn("sess-b", rows)
        self.assertNotIn("sess-c", rows)

        # Next run: limit has lifted, remaining sessions complete.
        self.run_pipeline(StubRunner([ENTRY_B, SKIP_MD]))
        statuses = self.session_statuses()
        self.assertEqual(statuses["sess-b"], "done")
        self.assertEqual(statuses["sess-c"], "done")
        rows = self.audit_rows()
        self.assertEqual(rows["sess-b"]["markdown"], ENTRY_B)
        self.assertEqual(rows["sess-c"]["skip"], 1)

    def test_invalid_output_marks_partial_and_retries_next_run(self):
        write_transcript(self.proj / "sess-bad.jsonl",
                          [("user", "task"), ("assistant", "done")])
        self.run_pipeline(StubRunner([""]))  # empty output: invalid, not cached
        self.assertEqual(self.session_statuses()["sess-bad"], "partial")
        self.assertNotIn("sess-bad", self.audit_rows())

        self.run_pipeline(StubRunner([ENTRY_A]))  # retried and completes
        self.assertEqual(self.session_statuses()["sess-bad"], "done")
        self.assertEqual(self.audit_rows()["sess-bad"]["markdown"], ENTRY_A)

    def test_refusal_output_marks_partial_and_is_not_cached(self):
        """Ticket #38: what-pass output violating the entry contract
        (refusal prose — neither SKIP nor ###-opening) is a failed call:
        partial, no audit row, nothing cached — the next run retries."""
        write_transcript(self.proj / "sess-refuse.jsonl",
                          [("user", "task"), ("assistant", "done")])
        self.run_pipeline(StubRunner([REFUSAL_MD]))
        self.assertEqual(self.session_statuses()["sess-refuse"], "partial")
        self.assertNotIn("sess-refuse", self.audit_rows())

        self.run_pipeline(StubRunner([ENTRY_A]))  # retried, not served stale
        self.assertEqual(self.session_statuses()["sess-refuse"], "done")
        self.assertEqual(self.audit_rows()["sess-refuse"]["markdown"], ENTRY_A)

    def test_gate_rejection_is_logged_to_stderr(self):
        """Ticket #79: a rejected what-pass output was silent and retried
        every night unseen. One stderr line names the cache file (session +
        part) and the head of the rejected text."""
        write_transcript(self.proj / "sess-loud.jsonl",
                          [("user", "task"), ("assistant", "done")])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.run_pipeline(StubRunner([REFUSAL_MD]))
        line = err.getvalue()
        self.assertIn("rejected sess-loud.part1.md", line)
        self.assertIn(REFUSAL_MD[:40], line)

    def test_what_prompt_brackets_the_extract(self):
        """Ticket #79 / ADR-0016: the extract is data between the
        instructions, not a live conversation appended after them — the
        output contract is the newest text the model sees."""
        write_transcript(self.proj / "sess-shape.jsonl",
                          [("user", "xylophone-79"), ("assistant", "done")])
        stub = StubRunner([ENTRY_A])
        self.run_pipeline(stub)
        prompt = stub.calls[-1]
        self.assertNotIn(analyze.EXTRACT_SLOT, prompt)
        self.assertLess(prompt.index("BEGIN TRANSCRIPT EXTRACT"), prompt.index("xylophone-79"))
        self.assertLess(prompt.index("xylophone-79"), prompt.index("END TRANSCRIPT EXTRACT"))
        self.assertLess(prompt.index("END TRANSCRIPT EXTRACT"), prompt.rindex("SKIP"))
        # a prefix-only template (what-v2) still assembles as before
        self.assertEqual(analyze.what_prompt("x", "instructions"), "instructions\nx")

    def test_poisoned_cached_what_output_is_recalled(self):
        """A refusal cached by a pre-#38 run fails the contract gate on
        read: the call re-runs instead of reusing the poisoned file."""
        write_transcript(self.proj / "sess-poison.jsonl",
                          [("user", "task"), ("assistant", "done")])
        cache = self.work / analyze.PROMPT_VERSION / "sess-poison.part1.md"
        cache.parent.mkdir(parents=True)
        cache.write_text(REFUSAL_MD)
        self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(self.session_statuses()["sess-poison"], "done")
        self.assertEqual(self.audit_rows()["sess-poison"]["markdown"], ENTRY_A)

    def test_command_boilerplate_never_reaches_the_what_pass(self):
        """Ticket #66: a slash-command message leads with whichever of
        <command-name>/<command-message>/<command-args> the client emitted
        first. extract.py checked only the first, so command-message-leading
        messages leaked into the extract — 89 of 359 cached extracts carried
        one, almost always as the opening piece."""
        write_transcript(self.proj / "sess-cmd.jsonl", [
            ("user", "<command-message>mattpocock-skills:wayfinder</command-message>"),
            ("user", "<command-name>/wayfinder</command-name>"),
            ("user", "<command-args>ticket 12</command-args>"),
            ("user", "chart the how-view"),
            ("assistant", "charted")])
        stub = StubRunner([ENTRY_A])
        self.run_pipeline(stub)

        prompt = stub.calls[-1]
        self.assertNotIn("<command-", prompt, "command boilerplate leaked into the extract")
        self.assertIn("chart the how-view", prompt)  # the real prompt survives

    def test_transcript_grown_after_extraction_is_reextracted(self):
        """Ticket #29: a session extracted mid-flight must not keep its
        truncated extract forever. Run 1 extracts and fails the what-pass
        (partial, extract cached); the transcript then grows; run 2's
        what-pass must see the grown transcript, not the stale cache."""
        path = self.proj / "sess-live.jsonl"
        write_transcript(path, FIXTURE_TURNS[:2])
        self.run_pipeline(StubRunner([""]))  # extract cached, what-pass fails
        self.assertEqual(self.session_statuses()["sess-live"], "partial")

        write_transcript(path, FIXTURE_TURNS)  # session was live: it grew
        stub = StubRunner([ENTRY_A])
        self.run_pipeline(stub)

        self.assertEqual(self.session_statuses()["sess-live"], "done")
        self.assertIn(FIXTURE_TURNS[2][1], stub.calls[-1],
                      "what-pass prompt built from stale truncated extract")

    def test_session_captured_within_the_window_stays_pending(self):
        """Issue #79's guard, judged from the records: a session whose newest
        raw record was captured in the last 5 minutes is not extracted, even
        though its file is quiet; once the capture is older it is audited."""
        path = self.proj / "sess-hot.jsonl"
        write_transcript(path, FIXTURE_TURNS)  # file mtime is old
        self.run_pipeline(StubRunner([]), live=True)  # captured now; no model call

        self.assertEqual(self.session_statuses()["sess-hot"], "pending")
        self.assertFalse(list((self.work / "extracts").glob("sess-hot.*")))

        settle_captures(self.db)
        self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(self.session_statuses()["sess-hot"], "done")

    def test_grains_rescanned_when_transcript_grew(self):
        """Ticket #29: growth invalidation covers the scanned grains too —
        usage/tool_events (and the adr_count derived from them) must reflect
        the full transcript, not the prefix scanned at first sight."""
        path = self.proj / "sess-grow.jsonl"
        recs = [rec("user", "u0", "2026-08-01T10:00:00Z", "do the task"),
                rec("assistant", "a0", "2026-08-01T10:00:05Z",
                    [{"type": "text", "text": "ok"}],
                    usage=USAGE, model="test-model", id="msg-0")]
        write_records(path, recs)
        self.run_pipeline(StubRunner([""]))  # what-pass fails: partial
        self.assertEqual(len(self.rows("SELECT * FROM usage")), 1)

        recs.append(rec("assistant", "a1", "2026-08-01T10:10:00Z",
                        [{"type": "text", "text": "more"}],
                        usage=USAGE, model="test-model", id="msg-1"))
        write_records(path, recs)
        self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(len(self.rows("SELECT * FROM usage")), 2)

    def _resume(self, name, extra):
        """A session taken to `done`, then resumed with `extra` more records."""
        path = self.proj / f"{name}.jsonl"
        # padded so the *file* is large while the extract stays one part
        # (extract.py truncates each message at PER_MSG_CAP): the re-audit
        # gate measures transcript bytes, the model cost measures parts.
        recs = [rec("user", "u0", "2026-08-01T10:00:00Z", "do the task"),
                rec("assistant", "a0", "2026-08-01T10:00:05Z",
                    [{"type": "text", "text": "ok " + "pad " * 5000}],
                    usage=USAGE, model="test-model", id="msg-0")]
        write_records(path, recs)
        self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(self.session_statuses()[name], "done")
        write_records(path, recs + extra)
        return path

    def test_resumed_done_session_tops_up_substrate(self):
        """Ticket #73: a `done` session that is resumed used to be skipped
        outright, so its whole tail — tokens included — never reached the db.
        The substrate is mechanical fact and is topped up whatever the
        status. Growth here is small, so the audit is NOT rewritten and no
        model call happens (StubRunner([]) would raise if one did)."""
        self._resume("sess-resume", [
            rec("assistant", "a1", "2026-08-01T10:10:00Z",
                [{"type": "text", "text": "a bit more"}],
                usage=USAGE, model="test-model", id="msg-1")])
        self.run_pipeline(StubRunner([]))

        self.assertEqual(len(self.rows(
            "SELECT * FROM usage WHERE session_id='sess-resume'")), 2,
            "resumed session's usage rows were dropped on the floor")
        self.assertEqual(self.session_statuses()["sess-resume"], "done")
        self.assertEqual(self.audit_rows()["sess-resume"]["markdown"], ENTRY_A)

    def test_live_resumed_session_is_topped_up_without_waiting(self):
        """Ticket #76's wipe is gone (ticket #87): derivation has no live
        guard and re-derives the captured records whole, so a session still
        being written is topped up in the same run, never left empty."""
        path = self._resume("sess-hotresume", [
            rec("assistant", "a1", "2026-08-01T10:10:00Z",
                [{"type": "text", "text": "a bit more"}],
                usage=USAGE, model="test-model", id="msg-1")])
        now = time.time()
        os.utime(path, (now, now))  # still being written
        self.run_pipeline(StubRunner([]))
        self.assertEqual(len(self.rows(
            "SELECT * FROM usage WHERE session_id='sess-hotresume'")), 2)

    def test_materially_grown_done_session_is_reaudited(self):
        """Ticket #73's other side: once REAUDIT_SHARE of the transcript is
        unseen, the entry is reporting a prefix as the whole and is rewritten
        — here from a resume far larger than the original session."""
        big = "grew " * 8000
        self._resume("sess-big", [
            rec("assistant", f"a{i}", f"2026-08-01T11:{i:02d}:00Z",
                [{"type": "text", "text": big}],
                usage=USAGE, model="test-model", id=f"msg-{i}")
            for i in range(1, 6)])
        self.run_pipeline(StubRunner([ENTRY_B]))

        self.assertEqual(self.audit_rows()["sess-big"]["markdown"], ENTRY_B,
                         "audit entry still describes only the first prefix")
        self.assertEqual(self.session_statuses()["sess-big"], "done")

    def test_subagent_transcripts_ride_the_growth_path_and_never_reaudit(self):
        """Issue #13: a subagent transcript unseen at sync (a db synced before
        the ticket, or an agent spawned after the parent went quiet) is picked
        up on the next run through the top-up path — no migration. The audit
        is blind to it by design: the entry, its watermark and the extract
        read the parent alone, so a subagent appearing or growing is never a
        model call (StubRunner([]) raises if one happens)."""
        parent = self.proj / "sess-sub.jsonl"
        recs = [rec("user", "u0", "2026-08-01T10:00:00Z", "do the task"),
                rec("assistant", "a0", "2026-08-01T10:00:05Z",
                    [{"type": "text", "text": "ok"}],
                    usage=USAGE, model="test-model", id="msg-p")]
        write_records(parent, recs)
        stub = StubRunner([ENTRY_A])
        self.run_pipeline(stub)
        watermark = self.rows("SELECT audited_size FROM sessions")[0]["audited_size"]
        self.assertEqual(watermark, parent.stat().st_size)

        sub = self.proj / "sess-sub" / "subagents" / "agent-a1.jsonl"
        big = "subagent secret text " * 3000  # far past REAUDIT_SHARE if counted
        write_records(sub, [
            {**rec("assistant", "s0", "2026-08-01T10:00:08Z",
                   [{"type": "text", "text": big}],
                   usage=USAGE, model="test-model", id="msg-s"),
             "sessionId": "sess-sub", "agentId": "a1", "isSidechain": True}])
        self.run_pipeline(StubRunner([]))

        self.assertEqual([u["agent_id"] for u in self.rows(
            "SELECT agent_id FROM usage WHERE session_id='sess-sub' ORDER BY at")],
            [None, "a1"])
        self.assertEqual(self.session_statuses()["sess-sub"], "done")
        self.assertEqual(self.audit_rows()["sess-sub"]["markdown"], ENTRY_A)
        self.assertEqual(self.rows("SELECT audited_size FROM sessions")[0]
                         ["audited_size"], watermark)
        self.assertNotIn("subagent secret", stub.calls[-1],
                         "the extract read a subagent transcript")

        # the subagent grows: topped up again, still no model call
        with sub.open("a") as f:
            for i in range(1, 3):
                f.write(json.dumps(
                    {**rec("assistant", f"s{i}", f"2026-08-01T10:0{i}:08Z",
                           [{"type": "text", "text": big}],
                           usage=USAGE, model="test-model", id=f"msg-s{i}"),
                     "sessionId": "sess-sub", "agentId": "a1", "isSidechain": True}) + "\n")
        _backdate(sub)
        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.rows("SELECT COUNT(*) n FROM usage"
                                   " WHERE agent_id='a1'")[0]["n"], 3)
        self.assertEqual(self.rows("SELECT COUNT(*) n FROM usage"
                                   " WHERE agent_id IS NULL")[0]["n"], 1)

    def test_why_pass_tables_dropped_from_pre_cut_db(self):
        """Ticket-#43 migration (ADR-0006): a db carrying the why-pass tables
        loses findings/evidence/runs and change_events.finding_id, keeping
        the change_events rows themselves."""
        self.db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db)
        conn.executescript("""
            CREATE TABLE findings (id INTEGER PRIMARY KEY, change TEXT);
            CREATE TABLE evidence (id INTEGER PRIMARY KEY, finding_id INTEGER);
            CREATE TABLE runs (id INTEGER PRIMARY KEY, resolution_rate REAL);
            CREATE TABLE change_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              observed_at TEXT NOT NULL, source TEXT NOT NULL,
              path TEXT NOT NULL, before_hash TEXT, after_hash TEXT,
              finding_id INTEGER REFERENCES findings(id));
            INSERT INTO findings VALUES (1, 'old finding');
            INSERT INTO change_events VALUES
              (1, '2026-08-01T00:00:00Z', 'snapshot', 'CLAUDE.md', NULL, 'h', 1);
        """)
        conn.commit()
        conn.close()

        conn = analyze.init_db(self.db)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertFalse({"findings", "evidence", "runs"} & tables)
            cols = [r[1] for r in conn.execute("PRAGMA table_info(change_events)")]
            self.assertNotIn("finding_id", cols)
            self.assertEqual(conn.execute(
                "SELECT path FROM change_events").fetchall(), [("CLAUDE.md",)])
        finally:
            conn.close()

    def test_init_db_switches_the_file_to_wal(self):
        """Issue #12: WAL is a property of the file, set once by whichever
        writer opens it first, so readers never queue behind a write."""
        conn = analyze.init_db(self.db)
        try:
            self.assertEqual(
                conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            conn.close()

    def _v1_session(self, sid):
        """A session row carried over from v1 with no raw records: its
        transcript was pruned before v2 ever captured it."""
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, project, transcript_path, date,"
                     " status) VALUES (?, 'p', ?, '2026-08-01', 'pending')",
                     (sid, str(self.proj / f"{sid}.jsonl")))
        conn.commit()
        conn.close()

    def test_session_with_neither_records_nor_extract_is_lost_for_good(self):
        """ADR-0015 as revised by issue #79: nothing captured and nothing
        cached — terminal, never selected again."""
        self._v1_session("sess-vanish")
        self.run_pipeline(StubRunner([]))  # no model call
        self.assertEqual(self.session_statuses()["sess-vanish"], "lost")
        self.assertNotIn("sess-vanish", self.audit_rows())

        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.session_statuses()["sess-vanish"], "lost")

    def test_captured_session_with_its_transcript_pruned_is_audited_not_lost(self):
        path = self.proj / "sess-pruned.jsonl"
        write_transcript(path, FIXTURE_TURNS)
        fire_capture(self.db, {"hook_event_name": "Stop", "transcript_path": str(path)})
        path.unlink()  # retention takes the file before any run extracts it

        settle_captures(self.db)
        stub = StubRunner([ENTRY_A])
        self.run_pipeline(stub)
        self.assertEqual(self.session_statuses()["sess-pruned"], "done")
        self.assertIn(FIXTURE_TURNS[2][1], stub.calls[0])

    def test_session_without_records_but_with_a_cached_extract_is_audited(self):
        src = Path(self.tmp.name) / "elsewhere" / "sess-cached.jsonl"
        write_transcript(src, FIXTURE_TURNS)
        (self.work / "extracts").mkdir(parents=True)
        subprocess.run([sys.executable, str(analyze.REPO / "cli" / "extract.py"),
                        str(src), str(self.work / "extracts" / "sess-cached")],
                       check=True, capture_output=True)
        self._v1_session("sess-cached")

        self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(self.session_statuses()["sess-cached"], "done")
        self.assertEqual(self.audit_rows()["sess-cached"]["markdown"], ENTRY_A)

    def test_reaudit_pending_session_pruned_keeps_entry_as_done(self):
        """A done session queued for re-audit (ADR-0013) whose transcript
        is then pruned still has its entry — it stands, prefix-semantic."""
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, project, transcript_path, date,"
                     " status) VALUES ('sess-re', 'p', '/gone', '2026-08-01', 'pending')")
        conn.execute("INSERT INTO audit (session_id, project, skip, markdown,"
                     " prompt_version, model) VALUES ('sess-re', 'p', 0, ?, 'v', 'm')",
                     (ENTRY_A,))
        analyze.classify_and_extract(conn, self.work)
        self.assertEqual(dict(conn.execute("SELECT id, status FROM sessions")),
                         {"sess-re": "done"})
        conn.close()

    def test_unextractable_records_stay_partial(self):
        """ExtractionFailed is retryable — only absence is terminal (ticket
        #78). A line that is not UTF-8 fails extract.py from the records as
        it did from the file."""
        path = self.proj / "sess-bad.jsonl"
        write_transcript(path, FIXTURE_TURNS)
        with path.open("ab") as f:
            f.write(b'{"type": "user", "message": {"content": "\xff\xfe"}}\n')
        _backdate(path)
        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.session_statuses()["sess-bad"], "partial")

    def test_raw_built_extract_and_map_equal_the_file_built_ones(self):
        """Issue #79: the extract is built from the parent's raw records in
        offset order and equals v1's, built from the file, byte for byte —
        multi-part, non-ASCII, command boilerplate, a file-tool marker, a
        malformed line and a subagent all included."""
        path = self.proj / "sess-eq.jsonl"
        write_transcript(path, big_turns() + [
            ("user", "<command-name>/x</command-name>"),
            ("assistant", "naïve café — 日本語 ✓")])
        with path.open("a") as f:
            f.write("not json at all\n")
            f.write(json.dumps(rec("assistant", "t1", "2026-08-01T10:00:00Z", [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "a.py"}}]))
                    + "\n")
        _backdate(path)
        write_transcript(self.proj / "sess-eq" / "subagents" / "agent-s1.jsonl",
                         [("assistant", "subagent text")])
        self.run_pipeline(StubRunner([LimitExhausted()]))  # greedy pass caches it

        v1 = Path(self.tmp.name) / "v1"
        v1.mkdir()
        subprocess.run([sys.executable, str(analyze.REPO / "cli" / "extract.py"),
                        str(path), str(v1 / "sess-eq")], check=True, capture_output=True)
        want = {p.name: p.read_bytes() for p in v1.iterdir()}
        got = {p.name: p.read_bytes() for p in (self.work / "extracts").glob("sess-eq.*")}
        self.assertGreater(len(want), 2, "fixture is not multi-part")
        self.assertEqual(got, want)

        # the local real-data check agrees on the same store
        sys.path.insert(0, str(analyze.REPO / "eval"))
        self.addCleanup(sys.path.remove, str(analyze.REPO / "eval"))
        import extract_equivalence
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(extract_equivalence.main(["--db", str(self.db)]), 0)
        self.assertIn("compared 1 session(s): 1 equal", out.getvalue())

    def test_reaudit_share_is_measured_on_captured_bytes(self):
        """Issue #79, ADR-0039 §7: growth the hook captured counts toward
        REAUDIT_SHARE even once the transcript is pruned, and `size` and
        the watermark are the registry high-water, never the file size."""
        path = self._resume("sess-cap", [
            rec("assistant", f"a{i}", f"2026-08-01T11:{i:02d}:00Z",
                [{"type": "text", "text": "grew " * 8000}]) for i in range(1, 4)])
        with path.open("a") as f:
            f.write('{"type": "user", "partial')  # a line still being written
        fire_capture(self.db, {"hook_event_name": "Stop", "transcript_path": str(path)})
        captured = path.stat().st_size - len('{"type": "user", "partial')
        path.unlink()

        settle_captures(self.db)
        self.run_pipeline(StubRunner([ENTRY_B]))
        self.assertEqual(self.audit_rows()["sess-cap"]["markdown"], ENTRY_B)
        [row] = self.rows("SELECT size, audited_size FROM sessions")
        self.assertEqual(row, {"size": captured, "audited_size": captured})

    def test_greedy_extract_caches_every_session_before_first_model_call(self):
        """Ticket #78's race: a session behind a limit pause used to sit
        unextracted until retention pruned it. Now every quiet session's
        extract is on disk before the model loop starts."""
        for n in ("a", "b", "c"):
            write_transcript(self.proj / f"sess-{n}.jsonl",
                              [("user", "task"), ("assistant", "done")])
        self.run_pipeline(StubRunner([analyze.LimitExhausted()]))  # pause on first call
        for n in ("a", "b", "c"):
            self.assertTrue((self.work / "extracts" / f"sess-{n}.map.json").exists())
        self.assertEqual(set(self.session_statuses().values()), {"pending"})

    def test_default_model_runner_timeout_returns_none(self):
        import subprocess as sp
        orig = analyze.subprocess.run

        def fake_run(*a, **k):
            raise sp.TimeoutExpired(cmd="claude", timeout=1)

        analyze.subprocess.run = fake_run
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                self.assertIsNone(analyze.default_model_runner("prompt"))
        finally:
            analyze.subprocess.run = orig
        self.assertIn("timed out", err.getvalue())  # an empty result says why

    def test_default_model_runner_failed_call_logs_its_exit(self):
        fake = subprocess.CompletedProcess([], 2, stdout="", stderr="auth expired")
        err = io.StringIO()
        with unittest.mock.patch.object(analyze.subprocess, "run", return_value=fake), \
                contextlib.redirect_stderr(err):
            self.assertIsNone(analyze.default_model_runner("prompt"))
        self.assertIn("exited 2: auth expired", err.getvalue())

    def test_default_model_runner_pauses_on_usage_stops_only(self):
        # The CLI's usage-stop lines pause the run, on either stream; other
        # failures that merely mention a limit fail the session, not the run.
        stops = [("You've hit your session limit \u00b7 resets 3pm", ""),
                 ("", "You\u2019ve reached your weekly limit"),
                 ("", "API Error: 429 spend limit reached \u00b7 resets Aug 8"),
                 ("", "You're out of usage credits"),
                 ("", 'API Error: 400 {"type":"error","error":{"type":"billing_error"}}')]
        others = ["Context limit reached \u00b7 /compact or /clear to continue",
                  "Subagent nesting limit reached (depth 3)", "output token limit exceeded",
                  "Error: line 429 of settings.json"]
        for stdout, stderr in stops:
            fake = subprocess.CompletedProcess([], 1, stdout=stdout, stderr=stderr)
            with unittest.mock.patch.object(analyze.subprocess, "run", return_value=fake):
                with self.assertRaises(analyze.LimitExhausted, msg=stdout or stderr):
                    analyze.default_model_runner("prompt")
        for stderr in others:
            fake = subprocess.CompletedProcess([], 1, stdout="", stderr=stderr)
            with unittest.mock.patch.object(analyze.subprocess, "run", return_value=fake), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertIsNone(analyze.default_model_runner("prompt"), stderr)

    def test_default_model_runner_has_no_tools_and_no_repo_cwd(self):
        # Transcript text in the prompt must not be able to drive tools or
        # inherit the repo's project permissions (security-preflight).
        fake = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        with unittest.mock.patch.object(analyze.subprocess, "run", return_value=fake) as run:
            self.assertEqual(analyze.default_model_runner("prompt"), "ok")
        args, kw = run.call_args
        cmd = args[0]
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", cmd)
        # the operator's hooks (plugin SessionStart text) must not reach the
        # model: one leaked a reply suffix into a status-v2 eval output (#96)
        self.assertEqual(json.loads(cmd[cmd.index("--settings") + 1]), {"disableAllHooks": True})
        cwd = Path(kw["cwd"])
        self.assertTrue(cwd.is_dir())
        self.assertNotEqual(cwd.resolve(), analyze.REPO.resolve())
        self.assertNotIn(analyze.REPO.resolve(), cwd.resolve().parents)

    def test_default_model_runner_pins_the_model_it_is_given(self):
        """#96: eval/run_v2.py compares models through the same restricted call."""
        fake = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        with unittest.mock.patch.object(analyze.subprocess, "run", return_value=fake) as run:
            analyze.default_model_runner("prompt")
            analyze.default_model_runner("prompt", model="other-model")
        pins = [c.args[0][c.args[0].index("--model") + 1] for c in run.call_args_list]
        self.assertEqual(pins, [analyze.MODEL, "other-model"])
        self.assertIn("--strict-mcp-config", run.call_args_list[1].args[0])

    def test_default_model_runner_missing_binary_pauses(self):
        # Ticket #84: no `claude` on PATH must pause the run like limit
        # exhaustion, not crash it with a FileNotFoundError traceback.
        orig = analyze.subprocess.run

        def fake_run(*a, **k):
            raise FileNotFoundError(2, "No such file or directory", "claude")

        analyze.subprocess.run = fake_run
        try:
            with self.assertRaises(analyze.LimitExhausted):
                analyze.default_model_runner("prompt")
        finally:
            analyze.subprocess.run = orig


class FolderIdentityTest(DbHelpers, unittest.TestCase):
    """Sync fills a session's folder identity and attribution source from
    what the capture hook recorded at its SessionStart (ticket #4, ADR-0018,
    ticket #84), driven through the capture hook and the analysis-run
    entrypoint over a fixture transcript root."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.proj = self.root / "test-project"
        self.folder = base / "repos" / "test-project"
        self.folder.mkdir(parents=True)

    def run_pipeline(self, model_runner):
        base = Path(self.tmp.name)
        run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                      model_runner=model_runner,
                      claude_dir=base / "claude", projects_dir=base / "repos")

    def identity_row(self, sid):
        return next(r for r in self.rows(
            "SELECT id, folder_identity, attribution_source FROM sessions")
            if r["id"] == sid)

    def test_sync_fills_identity_and_source_from_session_start(self):
        t = self.proj / "sess-id.jsonl"
        write_transcript(t, [("user", "add a feature"), ("assistant", "added")])
        session_start(self.db, t, self.folder)

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-id")
        self.assertEqual(row["folder_identity"], self.folder.stat().st_ino)
        self.assertEqual(row["attribution_source"], "hook")

    def test_sync_leaves_session_name_only_without_a_session_start(self):
        write_transcript(self.proj / "sess-noid.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-noid")
        self.assertIsNone(row["folder_identity"])
        self.assertIsNone(row["attribution_source"])

    def test_sync_falls_through_a_failed_session_start_firing_to_a_later_one(self):
        # A resumed session can fire SessionStart twice; the first firing's
        # stat failed, the second succeeded — the valid one must still be
        # picked up, not hidden by the first.
        t = self.proj / "sess-resumed.jsonl"
        write_transcript(t, [("user", "add a feature"), ("assistant", "added")])
        session_start(self.db, t, self.folder / "gone")
        session_start(self.db, t, self.folder)

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-resumed")
        self.assertEqual(row["folder_identity"], self.folder.stat().st_ino)
        self.assertEqual(row["attribution_source"], "hook")

    def test_sync_ignores_identity_on_other_events(self):
        t = self.proj / "sess-stop.jsonl"
        write_transcript(t, [("user", "add a feature"), ("assistant", "added")])
        fire_capture(self.db, {"hook_event_name": "Stop", "transcript_path": str(t),
                               "cwd": str(self.folder)})

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-stop")
        self.assertIsNone(row["folder_identity"])
        self.assertIsNone(row["attribution_source"])

    def test_migration_adds_identity_columns_without_losing_rows(self):
        """A pre-#4 db (user_version 5): init_db adds the two columns and
        every existing row survives, name-only, since there is nothing to
        backfill an identity from after the fact."""
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, transcript_path, status)"
                     " VALUES ('sess-old', '/t/a.jsonl', 'done')")
        conn.execute("PRAGMA user_version = 5")  # pre-#4 db
        conn.commit()
        conn.close()

        conn = analyze.init_db(self.db)
        try:
            self.assertEqual(
                conn.execute("PRAGMA user_version").fetchone()[0], 12)
        finally:
            conn.close()
        row = self.identity_row("sess-old")
        self.assertIsNone(row["folder_identity"])
        self.assertIsNone(row["attribution_source"])


class V10MigrationTest(DbHelpers, unittest.TestCase):
    """Ticket #84 (ADR-0031, ADR-0039 §1): the v10 migration over a v9
    database keeps every row, marks the derived rows `v1`, keeps the stored
    session day, and sets incremental auto-vacuum."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.db = self.base / "hindsight.db"

    def test_v9_rows_survive_and_derived_rows_are_v1(self):
        conn = sqlite3.connect(self.db)
        conn.executescript(analyze.SCHEMA)  # the v9 shape, but for audit.date
        conn.executescript("""
            ALTER TABLE audit ADD COLUMN date TEXT;  -- v9 had it; v11 drops it
            INSERT INTO sessions (id, project, transcript_path, date, status,
              skipped_records, audited_size)
              VALUES ('s-v1', 'p', '/gone/s-v1.jsonl', '2026-08-01', 'done', 0, 10);
            INSERT INTO audit (session_id, project, date, skip, markdown,
              prompt_version, model) VALUES ('s-v1', 'p', '2026-08-01', 0,
              '### Did', 'what-v3', 'm');
            INSERT INTO tool_events (session_id, name, error_text)
              VALUES ('s-v1', 'Edit', 'boom');
            INSERT INTO usage (session_id, at, input_tokens, output_tokens,
              cache_creation_input_tokens, cache_read_input_tokens)
              VALUES ('s-v1', '2026-08-01T10:00:00Z', 1, 2, 3, 4);
            INSERT INTO command_grains (session_id, command) VALUES ('s-v1', '/x');
            INSERT INTO field_histogram (session_id, version, scope, key, n)
              VALUES ('s-v1', '2.0', 'user', '*', 5);
            INSERT INTO breakage (at, tier, condition, old_version, new_version,
              key, old_share, new_share, since)
              VALUES ('2026-08-02T00:00:00Z', 'problem', 1, '1.0', '2.0',
              'user.x', 0.95, 0.1, '2026-08-01');
            PRAGMA user_version = 9;
        """)
        conn.close()

        run_analysis(root=self.base / "projects", db_path=self.db,
                     work_dir=self.base / "analysis", model_runner=StubRunner([]),
                     claude_dir=self.base / "claude", projects_dir=self.base / "repos")

        for table in ("tool_events", "usage", "command_grains", "field_histogram"):
            with self.subTest(table=table):
                self.assertEqual(self.rows(f"SELECT provenance FROM {table}"),
                                 [{"provenance": "v1"}])
        self.assertEqual(self.rows("SELECT error_text FROM tool_events"),
                         [{"error_text": "boom"}])
        self.assertEqual(self.rows("SELECT date, status, audited_size FROM sessions"),
                         [{"date": "2026-08-01", "status": "done", "audited_size": 10}])
        self.assertEqual(len(self.audit_rows()), 1)
        conn = sqlite3.connect(self.db)
        try:
            self.assertNotIn("date", {r[1] for r in conn.execute("PRAGMA table_info(audit)")})
        finally:
            conn.close()
        self.assertEqual(self.rows(
            "SELECT condition, key, old_share, new_share, since, source, session_id"
            " FROM breakage"),
            [{"condition": 1, "key": "user.x", "old_share": 0.95, "new_share": 0.1,
              "since": "2026-08-01", "source": None, "session_id": None}])
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 12)
            self.assertEqual(conn.execute("PRAGMA auto_vacuum").fetchone()[0], 2)
            self.assertIsNone(conn.execute("SELECT 1 FROM sqlite_master"
                                           " WHERE name='scan_runs'").fetchone())  # v12
            for table in ("raw_records", "transcripts", "records_index",
                          "deriver_state", "otel_histogram"):
                with self.subTest(table=table):
                    self.assertEqual(
                        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT source FROM health").fetchall(),
                             [("analysis",)], "the run writes its own row, nothing else")
        finally:
            conn.close()


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class BackstopTest(DbHelpers, unittest.TestCase):
    """Silent-change backstop (ticket #21), driven through the analysis-run
    entrypoint: blobs, silent baseline, change events from all three
    sources, idempotency. Capture only — renders nowhere in v1 (ADR-0006)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.root.mkdir()
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.claude = base / "claude"
        self.claude.mkdir()
        self.repos = base / "repos"
        self.repos.mkdir()

    def run_pipeline(self, model_runner=None):
        run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                      model_runner=model_runner or StubRunner([]),
                      claude_dir=self.claude, projects_dir=self.repos)

    def events(self):
        conn = sqlite3.connect(self.db)
        try:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in
                    conn.execute("SELECT * FROM change_events ORDER BY id")]
        finally:
            conn.close()

    def blob_hashes(self):
        conn = sqlite3.connect(self.db)
        try:
            return {r[0] for r in conn.execute("SELECT hash FROM blobs")}
        finally:
            conn.close()

    def test_narrative_failure_does_not_abort_the_run(self):
        """Ticket #77: the narrative pass is the only model-driven stage after
        the session loop, and `capture_backstop`/`scan_sunk_cost` run after it.
        A crash there used to escape `run_analysis` and cost both — the
        backstop is mechanical and must survive a bad model day."""
        (self.claude / "settings.json").write_text('{"a": 1}')
        orig = analyze.refresh_narratives
        analyze.refresh_narratives = lambda *a: (_ for _ in ()).throw(TypeError("bad shape"))
        self.addCleanup(setattr, analyze, "refresh_narratives", orig)
        self.run_pipeline()
        self.assertEqual(self.blob_hashes(), {sha('{"a": 1}')},
                         "backstop never ran: the narrative pass killed the run")

    def test_first_run_is_silent_baseline_with_blobs(self):
        (self.claude / "settings.json").write_text('{"a": 1}')
        (self.claude / "CLAUDE.md").write_text("# rules")
        self.run_pipeline()
        self.assertEqual(self.events(), [])
        self.assertEqual(self.blob_hashes(), {sha('{"a": 1}'), sha("# rules")})

    def test_config_edit_produces_one_event_with_hashes(self):
        (self.claude / "settings.json").write_text('{"a": 1}')
        self.run_pipeline()
        (self.claude / "settings.json").write_text('{"a": 2}')
        self.run_pipeline()

        events = self.events()
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["source"], "snapshot")
        self.assertEqual(ev["path"], "settings.json")
        self.assertEqual(ev["before_hash"], sha('{"a": 1}'))
        self.assertEqual(ev["after_hash"], sha('{"a": 2}'))
        # both versions retrievable for the render-time diff
        self.assertEqual(self.blob_hashes(), {sha('{"a": 1}'), sha('{"a": 2}')})

    def test_identical_content_stored_once(self):
        (self.claude / "settings.json").write_text("same content")
        (self.claude / "CLAUDE.md").write_text("same content")
        self.run_pipeline()
        self.assertEqual(self.blob_hashes(), {sha("same content")})

    def test_file_created_and_deleted_after_baseline(self):
        (self.claude / "settings.json").write_text("keep")
        self.run_pipeline()
        (self.claude / "CLAUDE.md").write_text("new file")
        self.run_pipeline()
        (self.claude / "CLAUDE.md").unlink()
        self.run_pipeline()

        events = self.events()
        self.assertEqual([(e["path"], e["before_hash"], e["after_hash"])
                          for e in events],
                         [("CLAUDE.md", None, sha("new file")),
                          ("CLAUDE.md", sha("new file"), None)])

    def test_second_run_with_no_changes_is_idempotent(self):
        (self.claude / "settings.json").write_text('{"a": 1}')
        self.run_pipeline()
        (self.claude / "settings.json").write_text('{"a": 2}')
        self.run_pipeline()
        self.run_pipeline()  # nothing changed since
        self.assertEqual(len(self.events()), 1)

    def plugins_json(self, plugins):
        return json.dumps({"version": 2, "plugins": plugins})

    def write_plugins(self, plugins):
        pf = self.claude / "plugins" / "installed_plugins.json"
        pf.parent.mkdir(exist_ok=True)
        pf.write_text(self.plugins_json(plugins))

    def test_plugins_structural_diff_per_plugin(self):
        v1 = {"ponytail@ponytail": [{"version": "4.8.4"}],
              "github@official": [{"version": "1.0"}]}
        self.write_plugins(v1)
        self.run_pipeline()  # baseline
        v2 = {"ponytail@ponytail": [{"version": "4.9.0"}],  # update
              "github@official": [{"version": "1.0"}],       # unchanged
              "impeccable@impeccable": [{"version": "2.0"}]}  # install
        self.write_plugins(v2)
        self.run_pipeline()

        events = self.events()
        self.assertEqual({e["source"] for e in events}, {"plugins-structural"})
        by_path = {e["path"]: e for e in events}
        self.assertEqual(set(by_path), {"ponytail@ponytail", "impeccable@impeccable"})
        before, after = sha(self.plugins_json(v1)), sha(self.plugins_json(v2))
        self.assertEqual(by_path["ponytail@ponytail"]["before_hash"], before)
        self.assertEqual(by_path["ponytail@ponytail"]["after_hash"], after)
        self.assertIsNone(by_path["impeccable@impeccable"]["before_hash"])
        self.assertEqual(by_path["impeccable@impeccable"]["after_hash"], after)

        self.run_pipeline()  # no further change: no new events
        self.assertEqual(len(self.events()), 2)

    def git_repo(self, name):
        repo = self.repos / name
        (repo / ".claude").mkdir(parents=True)
        self.git(repo, "init", "-q")
        return repo

    def git(self, repo, *args):
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t",
                        "-c", "user.name=t", *args], check=True,
                       capture_output=True)

    def commit(self, repo, path, content, msg):
        (repo / path).write_text(content)
        self.git(repo, "add", path)
        self.git(repo, "commit", "-q", "-m", msg)

    def test_project_git_commits_become_events(self):
        repo = self.git_repo("proj")
        self.commit(repo, ".claude/settings.json", '{"v": 1}', "init")
        self.run_pipeline()  # baseline: history predates tracking
        self.assertEqual(self.events(), [])

        self.commit(repo, ".claude/settings.json", '{"v": 2}', "tweak")
        self.run_pipeline()
        events = self.events()
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["source"], "project-git")
        self.assertEqual(ev["path"], "proj/.claude/settings.json")
        self.assertEqual(ev["before_hash"], sha('{"v": 1}'))
        self.assertEqual(ev["after_hash"], sha('{"v": 2}'))

        self.run_pipeline()  # no new commits: no new events
        self.assertEqual(len(self.events()), 1)


class PresenceTest(DbHelpers, unittest.TestCase):
    """Ticket #57 / ADR-0009, extended by ticket #5 / ADR-0018: the analysis
    run observes each project's workspace folder and stores the observation
    for the server to render — a history of (identity, name), not a per-run
    rewrite, so a rename keeps every name it has carried."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.projects = Path(self.tmp.name) / "Claude"
        (self.projects / "my-os" / "my-logs").mkdir(parents=True)
        (self.projects / "career-ops").mkdir()
        self.db = Path(self.tmp.name) / "h.db"

    def observe(self, *projects, observed_at=None):
        conn = analyze.init_db(self.db)
        try:
            conn.executemany(
                "INSERT OR IGNORE INTO sessions (id, project, transcript_path)"
                " VALUES (?, ?, 'x')", [(p, p) for p in projects])
            analyze.observe_presence(conn, self.projects, observed_at)
        finally:
            conn.close()
        return {r["name"]: r["present"]
                for r in self.rows("SELECT * FROM project_presence")}

    def test_dash_ambiguous_name_resolves_through_a_subdirectory(self):
        """`my-os-my-logs` is a session run in `my-os/my-logs`, not a project
        called that — one decoding of its dashes exists, so it is present."""
        self.assertEqual(analyze.resolve_folder(self.projects, "my-os-my-logs"),
                         self.projects / "my-os" / "my-logs")
        self.assertEqual(analyze.resolve_folder(self.projects, "career-ops"),
                         self.projects / "career-ops")
        self.assertIsNone(analyze.resolve_folder(self.projects, "career-ops-CLI"))
        self.assertIsNone(analyze.resolve_folder(self.projects, "my-logs"))

    def test_run_records_presence_per_project(self):
        self.assertEqual(
            self.observe("career-ops", "my-os-my-logs", "career-ops-CLI"),
            {"career-ops": 1, "my-os-my-logs": 1, "career-ops-CLI": 0})

    def test_unreadable_workspace_root_keeps_the_last_observation(self):
        """An unmounted or mistyped projects dir means "could not look", not
        "every folder is gone" — rewriting to all-absent would empty the chip
        row and claim a deletion that never happened."""
        before = self.observe("career-ops", "career-ops-CLI")
        conn = analyze.init_db(self.db)
        try:
            analyze.observe_presence(conn, self.projects / "nope")
        finally:
            conn.close()
        self.assertEqual(
            {r["name"]: r["present"]
             for r in self.rows("SELECT * FROM project_presence")}, before)

    def test_recreated_folder_returns_at_the_next_run(self):
        self.assertEqual(self.observe("gone")["gone"], 0)
        (self.projects / "gone").mkdir()
        self.assertEqual(self.observe("gone")["gone"], 1,
                         "each observation updates its name's row in place")

    def test_history_keeps_first_and_last_seen_across_runs(self):
        self.observe("career-ops", observed_at="2026-08-01T00:00:00Z")
        self.observe("career-ops", observed_at="2026-08-02T00:00:00Z")
        row = next(r for r in self.rows("SELECT * FROM project_presence")
                   if r["name"] == "career-ops")
        self.assertEqual((row["first_seen"], row["last_seen"]),
                         ("2026-08-01T00:00:00Z", "2026-08-02T00:00:00Z"))

    def test_migration_carries_old_presence_rows_forward(self):
        """A pre-#5 db (user_version 6, one row per name): init_db reshapes
        project_presence and every row survives as that name's first (and
        so far only) observation."""
        conn = analyze.init_db(self.db)
        conn.execute("DROP TABLE project_presence")
        conn.execute("CREATE TABLE project_presence (project TEXT PRIMARY KEY,"
                     " present INTEGER NOT NULL)")
        conn.execute("INSERT INTO project_presence VALUES ('old-project', 1)")
        conn.execute("PRAGMA user_version = 6")
        conn.commit()
        conn.close()

        conn = analyze.init_db(self.db)
        try:
            self.assertEqual(
                conn.execute("PRAGMA user_version").fetchone()[0], 12)
            row = conn.execute("SELECT folder_identity, name, present"
                               " FROM project_presence").fetchone()
        finally:
            conn.close()
        self.assertEqual(row, (None, "old-project", 1))


class IdentityFixture(DbHelpers):
    """A fixture transcript root beside a real workspace-folder tree, so
    folder identities are live inodes and the analysis run is driven end to
    end (ADR-0018 tests: rename, attribute, hook-row fill)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.repos = base / "repos"
        self.repos.mkdir()
        self.db = base / "hindsight.db"
        self.work = base / "analysis"

    def run_pipeline(self, model_runner):
        base = Path(self.tmp.name)
        with captured_earlier():
            run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                          model_runner=model_runner,
                          claude_dir=base / "claude", projects_dir=self.repos)

    def open_session(self, folder_name, sid, date="2026-08-01T10:00:00Z"):
        """A session opened with cwd = repos/folder_name — the transcript
        directory Claude Code encodes it under and the hook's stamped
        identity are both the folder's *live* state at this instant, exactly
        as sync_sessions sees it for real."""
        t = self.root / folder_name / f"{sid}.jsonl"
        write_transcript(t, [("user", "do work"), ("assistant", "done")], date=date)
        session_start(self.db, t, self.repos / folder_name)

    def identity_of(self):
        return {r["id"]: (r["folder_identity"], r["attribution_source"])
                for r in self.rows("SELECT id, folder_identity,"
                                   " attribution_source FROM sessions")}

    def project_of(self):
        return dict(sqlite3.connect(self.db).execute(
            "SELECT id, project FROM sessions"))


class RenameTest(IdentityFixture, unittest.TestCase):
    """Ticket #5 / ADR-0018: a rename is observed, never declared — presence
    confirms which of an identity's known names is live on disk right now,
    and canonicalisation re-keys every stale session (and its status-
    narrative row) to it, driven through the analysis-run entrypoint over a
    fixture transcript root and a real workspace-folder tree."""

    def test_narrative_survives_a_rename_without_a_model_call(self):
        """The ledger hash is over the runs, not the name (how.ledger_hash):
        a declaring project's stored narrative is re-keyed with its sessions
        and still matches the live ledger under the new name, so the
        narrative pass makes no call — the one call in the second run is
        the new session's what-pass."""
        import how
        (self.repos / "old-name").mkdir(parents=True)
        (self.repos / "old-name" / "local-process.md").write_text(
            "---\nstages:\n  - name: Build\n    skills: [tdd]\n---\n")
        self.open_session("old-name", "sess-1")
        self.run_pipeline(StubRunner([ENTRY_A]))

        conn = analyze.init_db(self.db)
        for i in range(3):
            conn.execute("INSERT INTO tool_events (session_id, name, at, consumer_type,"
                         " consumer) VALUES ('sess-1', 'Skill', ?, 'skill', 'tdd')",
                         (f"2026-08-01T10:0{i}:00Z",))
        d = how.how_data(conn, "old-name", self.repos)
        self.assertTrue(d["runs"], "fixture must yield a run, or the test is vacuous")
        h = how.ledger_hash(d)
        conn.execute("INSERT INTO status_narrative VALUES ('old-name', ?, '{\"Built\":"
                     " [], \"Reversed\": [], \"Now\": []}', ?, ?, '2026-08-01T00:00:00Z')",
                     (h, analyze.STATUS_VERSION, analyze.MODEL))
        conn.commit()
        conn.close()

        (self.repos / "old-name").rename(self.repos / "new-name")
        self.open_session("new-name", "sess-2", date="2026-08-05T10:00:00Z")
        stub = StubRunner([ENTRY_A])
        self.run_pipeline(stub)

        self.assertEqual(len(stub.calls), 1, "only sess-2's what-pass may call")
        conn = analyze.init_db(self.db)
        try:
            self.assertEqual(
                conn.execute("SELECT project, ledger_hash FROM status_narrative")
                    .fetchall(), [("new-name", h)])
            self.assertEqual(
                how.ledger_hash(how.how_data(conn, "new-name", self.repos)), h,
                "the re-keyed row still matches the live ledger under the new name")
        finally:
            conn.close()

    def presence_rows(self):
        return self.rows("SELECT folder_identity, name, present"
                         " FROM project_presence")

    def test_rename_between_two_runs_rekeys_sessions_and_narrative(self):
        (self.repos / "old-name").mkdir()
        self.open_session("old-name", "sess-1")
        self.run_pipeline(StubRunner([ENTRY_A]))

        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO status_narrative VALUES ('old-name', 'h',"
            " '{\"Built\": [], \"Reversed\": [], \"Now\": []}', 'status-v1',"
            " 'test-model', '2026-08-01T00:00:00Z')")
        conn.commit()
        conn.close()

        (self.repos / "old-name").rename(self.repos / "new-name")
        self.open_session("new-name", "sess-2")
        self.run_pipeline(StubRunner([ENTRY_A]))

        self.assertEqual(self.project_of(),
                         {"sess-1": "new-name", "sess-2": "new-name"})
        narratives = {r[0] for r in sqlite3.connect(self.db).execute(
            "SELECT project FROM status_narrative")}
        self.assertEqual(narratives, {"new-name"})
        presence = {r["name"]: r["present"] for r in self.presence_rows()}
        self.assertEqual(presence, {"old-name": 0, "new-name": 1})

    def test_borrowed_name_never_merges_two_different_identities(self):
        """`hindsight`, briefly reused by a second, unrelated folder while
        the first sits permanently renamed away (ADR-0018's motivating
        case): a session is attributed to its own folder by identity,
        whatever the transcript directory is called — never merged just
        because two folders shared a name at different times."""
        (self.repos / "hindsight").mkdir()
        self.open_session("hindsight", "sess-old")
        self.run_pipeline(StubRunner([ENTRY_A]))
        (self.repos / "hindsight").rename(self.repos / "hindsight-old")

        (self.repos / "hindsight").mkdir()  # a second, unrelated folder
        self.open_session("hindsight", "sess-borrow")
        (self.repos / "hindsight").rename(self.repos / "hindsight-new")
        self.open_session("hindsight-new", "sess-fork")
        self.run_pipeline(StubRunner([ENTRY_A, ENTRY_A]))

        projects = self.project_of()
        self.assertEqual(projects["sess-old"], "hindsight-old",
                         "found by inode in the workspace root, though no"
                         " session has opened under the new name")
        self.assertEqual(projects["sess-borrow"], "hindsight-new")
        self.assertEqual(projects["sess-fork"], "hindsight-new")

    def test_rename_is_seen_before_any_session_opens_under_the_new_name(self):
        """The run after a rename finds the folder by inode: its sessions
        re-key and its chip stays live, with nothing having happened in
        the folder since. A folder moved out of the workspace root has no
        name to find, and is left as it was."""
        (self.repos / "old-name").mkdir()
        self.open_session("old-name", "sess-1")
        self.run_pipeline(StubRunner([ENTRY_A]))

        (self.repos / "old-name").rename(self.repos / "new-name")
        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.project_of(), {"sess-1": "new-name"})
        presence = {r["name"]: r["present"] for r in self.presence_rows()}
        self.assertEqual(presence, {"old-name": 0, "new-name": 1})

        (self.repos / "new-name").rename(Path(self.tmp.name) / "away")
        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.project_of(), {"sess-1": "new-name"})
        presence = {r["name"]: r["present"] for r in self.presence_rows()}
        self.assertEqual(presence, {"old-name": 0, "new-name": 0})

    def test_folder_deleted_after_a_rename_hides_under_its_current_name(self):
        (self.repos / "old-name").mkdir()
        self.open_session("old-name", "sess-1")
        self.run_pipeline(StubRunner([ENTRY_A]))
        (self.repos / "old-name").rename(self.repos / "new-name")
        self.open_session("new-name", "sess-2")
        self.run_pipeline(StubRunner([ENTRY_A]))

        shutil.rmtree(self.repos / "new-name")
        self.run_pipeline(StubRunner([]))  # nothing new to sync or call

        presence = {r["name"]: r["present"] for r in self.presence_rows()}
        self.assertEqual(presence["new-name"], 0)
        self.assertEqual(set(self.project_of().values()), {"new-name"},
                         "hides under its current name, not reverted to the old one")

    def test_name_only_session_in_a_reused_name_stays_where_synced(self):
        """A pre-hook session carries no identity — canonicalisation only
        ever re-keys sessions with a folder identity, so a name-only row is
        untouched even when an identified project later reuses its name.
        No date rule, no heuristic."""
        (self.repos / "reused").mkdir()
        identity = (self.repos / "reused").stat().st_ino
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, project, transcript_path)"
                     " VALUES ('sess-pre-hook', 'reused', 'x')")
        conn.execute(
            "INSERT INTO sessions (id, project, transcript_path,"
            " folder_identity, attribution_source) VALUES"
            " ('sess-hooked', 'reused', 'x', ?, 'hook')", (identity,))
        conn.commit()
        conn.close()

        (self.repos / "reused").rename(self.repos / "renamed")
        conn = analyze.init_db(self.db)
        conn.execute(
            "INSERT INTO sessions (id, project, transcript_path,"
            " folder_identity, attribution_source) VALUES"
            " ('sess-hooked-2', 'renamed', 'x', ?, 'hook')", (identity,))
        conn.commit()
        analyze.observe_presence(conn, self.repos)
        analyze.canonicalize_projects(conn)
        projects = dict(conn.execute("SELECT id, project FROM sessions"))
        conn.close()

        self.assertEqual(projects["sess-pre-hook"], "reused")
        self.assertEqual(projects["sess-hooked"], "renamed")
        self.assertEqual(projects["sess-hooked-2"], "renamed")


class AttributeTest(IdentityFixture, unittest.TestCase):
    """Ticket #7 / ADR-0018: the operator's escape hatch for pre-hook
    history. `attribute` stamps a live folder's identity onto the name-only
    sessions synced under a name; the *next* run re-keys them through the
    ordinary canonicalisation path. Plus the hook-row race fill from #5's
    review: a session synced before its SessionStart row landed gains its
    identity on the next run, no operator needed."""

    def sync_name_only(self, folder_name, *sids_and_dates):
        """Transcripts under folder_name with no SessionStart — pre-hook history
        — synced by one pipeline run. Returns the folder's live inode."""
        (self.repos / folder_name).mkdir(exist_ok=True)
        for sid, date in sids_and_dates:
            write_transcript(self.root / folder_name / f"{sid}.jsonl",
                              [("user", "do work"), ("assistant", "done")],
                              date=date)
        self.run_pipeline(StubRunner([ENTRY_A] * len(sids_and_dates)))
        return (self.repos / folder_name).stat().st_ino

    def attribute(self, name, folder, before=None):
        conn = analyze.init_db(self.db)
        try:
            return analyze.attribute_sessions(conn, name, folder, before,
                                              projects_dir=self.repos)
        finally:
            conn.close()

    def main(self, *argv):
        return analyze.main(["attribute", *argv, "--db", str(self.db),
                             "--projects-dir", str(self.repos)])

    def test_stamps_every_name_only_session_and_the_next_run_rekeys(self):
        """The motivating repair: every session under the old name predates
        the hook, and no hook-stamped session has opened under the new one
        — the command alone must be enough for the next run to re-key."""
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"),
                            ("s-2", "2026-08-02T10:00:00Z"))
        (self.repos / "legacy").rename(self.repos / "legacy-now")

        self.assertEqual(self.attribute("legacy", self.repos / "legacy-now"), 2)
        ident = (self.repos / "legacy-now").stat().st_ino
        self.assertEqual(self.identity_of(),
                         {"s-1": (ident, "operator"), "s-2": (ident, "operator")})
        self.assertEqual(self.project_of()["s-1"], "legacy",
                         "attribute does not re-key; the next run does")

        self.run_pipeline(StubRunner([]))
        self.assertEqual(set(self.project_of().values()), {"legacy-now"})
        presence = {r["name"]: r["present"] for r in self.rows(
            "SELECT name, present FROM project_presence")}
        self.assertEqual(presence, {"legacy": 0, "legacy-now": 1})

    def test_never_overwrites_a_session_already_carrying_an_identity(self):
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"))
        self.open_session("legacy", "s-hooked", "2026-08-03T10:00:00Z")
        self.run_pipeline(StubRunner([ENTRY_A]))
        hooked = self.identity_of()["s-hooked"]
        self.assertEqual(hooked[1], "hook")

        (self.repos / "elsewhere").mkdir()
        self.assertEqual(self.attribute("legacy", self.repos / "elsewhere"), 1)
        ids = self.identity_of()
        self.assertEqual(ids["s-hooked"], hooked)
        self.assertEqual(ids["s-1"],
                         ((self.repos / "elsewhere").stat().st_ino, "operator"))

    def test_before_stamps_only_sessions_first_seen_before_it(self):
        self.sync_name_only("legacy", ("s-early", "2026-08-01T10:00:00Z"),
                            ("s-late", "2026-08-10T10:00:00Z"))
        (self.repos / "elsewhere").mkdir()
        n = self.attribute("legacy", self.repos / "elsewhere",
                           before="2026-08-05T00:00:00Z")
        self.assertEqual(n, 1)
        ids = self.identity_of()
        self.assertEqual(ids["s-early"],
                         ((self.repos / "elsewhere").stat().st_ino, "operator"))
        self.assertEqual(ids["s-late"], (None, None))

    def test_before_compares_instants_not_strings(self):
        """A fractional-second transcript stamp sorts *below* a whole-second
        bound as text ('.' < 'Z') though it is later in time."""
        self.sync_name_only("legacy", ("s-1", "2026-08-05T00:00:00.500Z"))
        (self.repos / "elsewhere").mkdir()
        self.assertEqual(self.attribute("legacy", self.repos / "elsewhere",
                                        before="2026-08-05T00:00:00Z"), 0)

    def test_before_decides_a_gone_transcript_by_its_stored_day(self):
        """Ticket #8 found 39 pruned-transcript sessions under the motivating
        repair: with no first record to read, a bound left them alone and the
        unbounded second call swept them onto the wrong folder. The stored
        day bucket is derived from that same first record, so a day strictly
        before the bound's day is decisive; the bound's own day is not."""
        self.sync_name_only("legacy", ("s-gone-early", "2026-08-01T10:00:00Z"),
                            ("s-gone-same-day", "2026-08-05T12:00:00Z"))
        for sid in ("s-gone-early", "s-gone-same-day"):
            (self.root / "legacy" / f"{sid}.jsonl").unlink()
        conn = analyze.init_db(self.db)  # a head with no timestamp syncs as ''
        conn.execute("INSERT INTO sessions (id, project, transcript_path, date)"
                     " VALUES ('s-gone-undated', 'legacy', 'x', '')")
        conn.commit()
        conn.close()
        (self.repos / "elsewhere").mkdir()
        n = self.attribute("legacy", self.repos / "elsewhere",
                           before="2026-08-05T12:00:00Z")
        self.assertEqual(n, 1)
        ids = self.identity_of()
        self.assertEqual(ids["s-gone-early"],
                         ((self.repos / "elsewhere").stat().st_ino, "operator"))
        self.assertEqual(ids["s-gone-same-day"], (None, None))
        self.assertEqual(ids["s-gone-undated"], (None, None))

    def test_second_identical_call_touches_zero_rows(self):
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"))
        (self.repos / "elsewhere").mkdir()
        self.assertEqual(self.attribute("legacy", self.repos / "elsewhere"), 1)
        self.assertEqual(self.attribute("legacy", self.repos / "elsewhere"), 0)

    def assert_refused(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            self.main(*argv)
        self.assertNotEqual(cm.exception.code, 0)
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1)
        self.assertEqual(self.identity_of()["s-1"], (None, None), "no write")
        self.assertEqual(self.rows("SELECT * FROM project_presence"
                                   " WHERE folder_identity IS NOT NULL"), [])

    def test_missing_folder_is_refused_with_no_write(self):
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"))
        self.assert_refused("legacy", str(self.repos / "nope"))

    def test_folder_outside_the_workspace_root_is_refused(self):
        """No encoded name can exist for it, so a stamp could never re-key."""
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"))
        self.assert_refused("legacy", self.tmp.name)

    def test_mistyped_name_touches_zero_rows_and_says_so(self):
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"))
        (self.repos / "elsewhere").mkdir()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.main("legacyy", str(self.repos / "elsewhere"))
        self.assertIn("0 session", out.getvalue())
        self.assertEqual(self.identity_of()["s-1"], (None, None))

    def test_subcommand_prints_the_count_it_changed(self):
        self.sync_name_only("legacy", ("s-1", "2026-08-01T10:00:00Z"),
                            ("s-2", "2026-08-02T10:00:00Z"))
        (self.repos / "elsewhere").mkdir()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.main("legacy", str(self.repos / "elsewhere"),
                      "--before", "2026-08-02T00:00:00Z")
        self.assertIn("1 session", out.getvalue())

    def test_hook_row_that_landed_after_sync_fills_on_the_next_run(self):
        """The hook-row race (#5's review): sync ran before the capture
        hook recorded the SessionStart identity. The per-run fill catches
        it; a session with no identity recorded stays name-only."""
        ident = self.sync_name_only("proj", ("s-raced", "2026-08-01T10:00:00Z"),
                                    ("s-prehook", "2026-08-01T11:00:00Z"))
        self.assertEqual(self.identity_of()["s-raced"], (None, None))
        session_start(self.db, self.root / "proj" / "s-raced.jsonl", self.repos / "proj")
        self.run_pipeline(StubRunner([]))
        self.assertEqual(self.identity_of(), {"s-raced": (ident, "hook"),
                                              "s-prehook": (None, None)})


class ZoneTest(DbHelpers, unittest.TestCase):
    """Issue #1: `HINDSIGHT_TZ` pins the day-bucket zone; unset is the host
    zone (ADR-0014 as amended). Both bucket paths go through libc, so the
    one setting moves them together and they cannot drift."""
    EVE = "2026-08-29T00:13:55Z"  # 20:13 EDT on the 28th, 09:13 JST on the 29th

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "h.db"
        self.root = Path(self.tmp.name) / "projects"
        # Whatever a case sets, the suite's pin comes back afterwards.
        self.addCleanup(os.environ.pop, "HINDSIGHT_TZ", None)
        self.addCleanup(self.pin, "America/New_York")

    def pin(self, name):
        os.environ["HINDSIGHT_TZ"] = name
        analyze.apply_tz()

    def sql_day(self):
        with contextlib.closing(sqlite3.connect(":memory:")) as c:
            return c.execute(f"SELECT {analyze.day_sql('?')}",
                             (self.EVE,)).fetchone()[0]

    def test_hindsight_tz_moves_both_bucket_paths_together(self):
        self.pin("Asia/Tokyo")
        self.assertEqual((analyze.local_day(self.EVE), self.sql_day()),
                         ("2026-08-29", "2026-08-29"))
        self.pin("America/New_York")
        self.assertEqual((analyze.local_day(self.EVE), self.sql_day()),
                         ("2026-08-28", "2026-08-28"))

    def test_invalid_zone_warns_once_and_keeps_the_host_zone(self):
        os.environ["HINDSIGHT_TZ"] = "Not/AZone"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            analyze.apply_tz()
        # Count its own line: the redirect is global, and the runner's
        # warning display drops other modules' ResourceWarnings in here.
        self.assertEqual([l for l in err.getvalue().splitlines() if "HINDSIGHT_TZ" in l],
                         ["HINDSIGHT_TZ='Not/AZone' is not an IANA zone name;"
                          " using the host zone"])
        self.assertEqual(os.environ["TZ"], "America/New_York")  # untouched
        self.assertEqual(analyze.local_day(self.EVE), "2026-08-28")

    def test_raw_session_dates_from_its_earliest_record_v1_keeps_its_day(self):
        """Ticket #86 (ADR-0031 §5): a `raw` session stores no day; every
        view reads the stored day, else the local day of the earliest
        records-index timestamp, parent and subagents together, bucketed
        at read under HINDSIGHT_TZ. A `v1` session keeps its stored day."""
        base = Path(self.tmp.name)
        parent = self.root / "p" / "sess-eve.jsonl"
        write_records(parent, [rec("user", "u0", "2026-08-29T05:00:00Z", "hi")])
        write_records(parent.with_suffix("") / "subagents" / "agent-x.jsonl",
                      [rec("user", "x0", self.EVE, "sub")])
        write_records(self.root / "p" / "sess-old.jsonl",
                      [rec("user", "o0", self.EVE, "old")])
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, project, transcript_path, date, status)"
                     " VALUES ('sess-old', 'p', 'x', '2026-08-01', 'done')")
        conn.commit()
        conn.close()
        run_analysis(root=self.root, db_path=self.db, work_dir=base / "analysis",
                     model_runner=StubRunner([SKIP_MD]),
                     claude_dir=base / "claude", projects_dir=base / "repos")
        self.assertIsNone(self.rows("SELECT date FROM sessions WHERE id='sess-eve'")[0]["date"])
        day = lambda: {r["id"]: r["d"] for r in self.rows(  # noqa: E731
            f"SELECT s.id, {analyze.session_day('s')} AS d FROM sessions s")}
        self.assertEqual(day(), {"sess-eve": "2026-08-28", "sess-old": "2026-08-01"})
        self.pin("Asia/Tokyo")
        self.assertEqual(day(), {"sess-eve": "2026-08-29", "sess-old": "2026-08-01"})


class SweepDeriveTest(DbHelpers, unittest.TestCase):
    """Ticket #86 (ADR-0031 §5-6, ADR-0033 §1, ADR-0037 §6): the sweep
    catches up what no firing captured, sessions are known from the
    registry, and the deriver loop builds the records index from the raw
    store, driven through the analysis run."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.proj = self.root / "test-project"

    def run_pipeline(self, model_runner=None):
        base = Path(self.tmp.name)
        with contextlib.redirect_stderr(io.StringIO()):
            run_analysis(root=self.root, db_path=self.db, work_dir=base / "analysis",
                         model_runner=model_runner or StubRunner([SKIP_MD] * 10),
                         claude_dir=base / "claude", projects_dir=base / "repos")

    def patch(self, name, value):
        orig = getattr(analyze, name)
        setattr(analyze, name, value)
        self.addCleanup(setattr, analyze, name, orig)

    def write(self, sid, n, start=0):
        write_records(self.proj / f"{sid}.jsonl",
                      [rec("user", f"{sid}-{i}", f"2026-08-01T10:00:{i:02}Z", f"turn {i}")
                       for i in range(start, start + n)])

    def append(self, path, *lines):
        with open(path, "a") as f:
            f.writelines(line + "\n" for line in lines)
        _backdate(path)

    def stored(self, sid, agent=None):
        import zlib
        return b"".join(zlib.decompress(r["line"]) for r in self.rows(
            "SELECT line FROM raw_records WHERE session_id=? AND agent_id IS ?"
            " ORDER BY byte_offset", (sid, agent)))

    def index(self, sid):
        return self.rows("SELECT agent_id, byte_offset, type, uuid, timestamp, provenance"
                         " FROM records_index WHERE session_id=? ORDER BY byte_offset",
                         (sid,))

    def test_transcript_with_no_firing_is_captured_by_the_sweep(self):
        self.write("sess-a", 2)
        sub = self.proj / "sess-a" / "subagents" / "agent-x1.jsonl"
        write_records(sub, [rec("user", "x-0", "2026-08-01T10:00:05Z", "sub")])
        hooked = self.proj / "sess-h.jsonl"
        write_records(hooked, [rec("user", "h-0", "2026-08-01T11:00:00Z", "hi")])
        fire_capture(self.db, {"hook_event_name": "Stop", "transcript_path": str(hooked)})
        self.append(hooked, json.dumps(rec("user", "h-1", "2026-08-01T11:00:01Z", "more")))

        self.run_pipeline()

        for sid, agent, path in (("sess-a", None, self.proj / "sess-a.jsonl"),
                                 ("sess-a", "x1", sub), ("sess-h", None, hooked)):
            with self.subTest(sid=sid, agent=agent):
                self.assertEqual(self.stored(sid, agent), path.read_bytes())
                self.assertEqual(self.rows(
                    "SELECT high_water FROM transcripts WHERE session_id=?"
                    " AND agent_id IS ?", (sid, agent)), [{"high_water": path.stat().st_size}])
        self.assertEqual(self.rows("SELECT id, project FROM sessions ORDER BY id"),
                         [{"id": "sess-a", "project": "test-project"},
                          {"id": "sess-h", "project": "test-project"}])
        self.assertEqual(sorted(r["uuid"] for r in self.index("sess-a")),
                         ["sess-a-0", "sess-a-1", "x-0"])

    def test_grown_session_is_rederived_whole_and_an_unchanged_one_is_not_touched(self):
        self.write("sess-a", 2)
        self.write("sess-b", 2)
        self.run_pipeline()
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE records_index SET type='tampered'")
        conn.commit()
        conn.close()
        self.append(self.proj / "sess-a.jsonl",
                    json.dumps(rec("assistant", "sess-a-2", "2026-08-01T10:01:00Z", "x")))

        self.run_pipeline()

        self.assertEqual([(r["type"], r["uuid"], r["provenance"]) for r in self.index("sess-a")],
                         [("user", "sess-a-0", "raw"), ("user", "sess-a-1", "raw"),
                          ("assistant", "sess-a-2", "raw")])
        self.assertEqual({r["type"] for r in self.index("sess-b")}, {"tampered"})

    def test_a_deriver_raising_on_one_session_leaves_it_due_and_derives_the_others(self):
        self.write("sess-a", 2)
        self.write("sess-b", 2)
        real = analyze.index_records

        def poisoned(conn, sid, records):
            if sid == "sess-a":
                raise ValueError("poison")
            return real(conn, sid, records)

        self.patch("index_records", poisoned)
        self.run_pipeline()
        self.assertEqual(self.index("sess-a"), [])
        self.assertEqual(len(self.index("sess-b")), 2)
        [health] = self.rows("SELECT error_text FROM health WHERE source='analysis'")
        self.assertIn("derivation", health["error_text"])
        self.assertIn("sess-a", health["error_text"])

        analyze.index_records = real
        self.run_pipeline()
        self.assertEqual(len(self.index("sess-a")), 2)

    def test_records_index_version_bump_rebuilds_raw_rows_only(self):
        self.write("sess-a", 2)
        self.run_pipeline()
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM records_index WHERE byte_offset=0")
        conn.executemany("INSERT INTO records_index (session_id, byte_offset, type,"
                         " provenance) VALUES (?, ?, 'old', ?)",
                         [("sess-a", 99999, "v1"), ("sess-gone", 0, "compacted")])
        conn.commit()
        conn.close()
        self.run_pipeline()
        self.assertEqual(len(self.index("sess-a")), 2, "an unchanged session was re-derived")

        self.patch("RECORDS_INDEX_VERSION", analyze.RECORDS_INDEX_VERSION + 1)
        self.run_pipeline()

        self.assertEqual([(r["byte_offset"] == 0, r["provenance"]) for r in self.index("sess-a")],
                         [(True, "raw"), (False, "raw"), (False, "v1")])
        self.assertEqual([(r["type"], r["provenance"]) for r in self.index("sess-gone")],
                         [("old", "compacted")])

    def test_an_unparseable_stored_line_writes_one_condition_5_breakage(self):
        path = self.proj / "sess-bad.jsonl"
        write_records(path, [rec("user", "u0", "2026-08-01T10:00:00Z", "hi"),
                             "{not json", "[1, 2]"])
        self.run_pipeline()
        self.append(path, "also not json")
        self.run_pipeline()

        rows = self.rows("SELECT tier, session_id, acknowledged_at FROM breakage"
                         " WHERE condition=5")
        self.assertEqual(rows, [{"tier": "problem", "session_id": "sess-bad",
                                 "acknowledged_at": None}])
        self.assertEqual([r["uuid"] for r in self.index("sess-bad")], ["u0"])
        [row] = self.rows(f"SELECT {', '.join(analyze.BREAKAGE_COLS)} FROM breakage")
        self.assertIn("sess-bad", analyze.breakage_text(row))

    def test_a_non_utf8_line_still_gets_its_condition_5_row_and_others_derive(self):
        self.write("sess-bad", 1)
        with open(self.proj / "sess-bad.jsonl", "ab") as f:
            f.write(b"\xff\xfe not utf-8\n")
        _backdate(self.proj / "sess-bad.jsonl")
        self.write("sess-ok", 2)

        self.run_pipeline()

        self.assertEqual(self.rows("SELECT session_id FROM breakage WHERE condition=5"),
                         [{"session_id": "sess-bad"}])
        self.assertEqual([r["uuid"] for r in self.index("sess-bad")], ["sess-bad-0"])
        self.assertEqual(len(self.index("sess-ok")), 2)
        self.assertEqual(self.rows("SELECT id FROM sessions WHERE skipped_records IS NULL"), [])
        [health] = self.rows("SELECT error_text FROM health WHERE source='analysis'")
        self.assertNotIn("derivation", health["error_text"] or "")

    def test_a_directory_named_like_a_transcript_is_not_swept(self):
        (self.proj / "s1.jsonl").mkdir(parents=True)
        self.write("sess-ok", 2)

        self.run_pipeline()

        [health] = self.rows("SELECT error_text FROM health WHERE source='analysis'")
        self.assertNotIn("sweep", health["error_text"] or "")

    @unittest.skipIf(os.geteuid() == 0, "chmod(0) does not stop root reading")
    def test_an_unreadable_transcript_path_fails_the_sweep_alone(self):
        self.write("s1", 1)
        (self.proj / "s1.jsonl").chmod(0)
        self.addCleanup((self.proj / "s1.jsonl").chmod, 0o644)
        self.write("sess-ok", 2)

        self.run_pipeline()

        self.assertEqual(self.stored("sess-ok"), (self.proj / "sess-ok.jsonl").read_bytes())
        [health] = self.rows("SELECT error_text FROM health WHERE source='analysis'")
        self.assertIn("sweep", health["error_text"])
        self.assertIn("s1.jsonl", health["error_text"])

    def test_v11_drops_the_audit_date(self):
        self.run_pipeline()
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 12)
            self.assertNotIn("date", {r[1] for r in conn.execute("PRAGMA table_info(audit)")})
        finally:
            conn.close()


class NarrativeTest(DbHelpers, unittest.TestCase):
    """The status-narrative pass (ADR-0012, ticket #68): ledger-keyed,
    write-time gated by eval/score.py's contract floors, never on read."""
    STANDING = ["Ship OTLP listener (Aug 16)", "Wire telemetry for the OTLP listener (Aug 16)",
                "Build: OTLP listener and telemetry wired (Aug 16)"]
    NOW = ["Build, since Aug 16: OTLP listener"]
    GOOD = json.dumps({"Standing": STANDING, "Superseded": [], "Now": NOW})

    def adr(self, status):
        f = self.projects / "p" / "docs" / "adr" / "0001-otlp.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# ADR-0001: OTLP listener ingest\n\n"
                     f"**Date:** 2026-08-01 · **Status:** {status}\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "h.db"
        self.projects = Path(self.tmp.name) / "projects"
        (self.projects / "p").mkdir(parents=True)
        (self.projects / "p" / "local-process.md").write_text(
            "---\nstages:\n  - name: Build\n    skills: [tdd]\n---\n")
        self.conn = analyze.init_db(self.db)
        self.conn.execute("INSERT INTO sessions (id, project, transcript_path, date, status)"
                          " VALUES ('s1', 'p', '/x', '2026-08-16', 'done')")
        self.conn.execute("INSERT INTO audit VALUES ('s1', 'p', 0,"
                          " '### Ship OTLP listener and wire telemetry', 'what-v2', 'm', 0)")
        for i in range(3):
            self.conn.execute("INSERT INTO tool_events (session_id, name, at, consumer_type,"
                              " consumer) VALUES ('s1', 'Skill', ?, 'skill', 'tdd')",
                              (f"2026-08-16T10:0{i}:00Z",))
        self.conn.commit()

    def stored(self):
        return self.conn.execute("SELECT project, narrative, prompt_version, model"
                                 " FROM status_narrative").fetchall()

    def test_valid_output_stored_keyed_on_ledger(self):
        calls = []
        runner = lambda p: calls.append(p) or self.GOOD
        analyze.refresh_narratives(self.conn, self.projects, runner)
        self.assertEqual(self.stored(), [("p", self.GOOD, "status-v2", analyze.MODEL)])
        self.assertIn('"stage": "Build"', calls[0])
        analyze.refresh_narratives(self.conn, self.projects, runner)
        self.assertEqual(len(calls), 1)  # unchanged ledger: no second call

    def test_adr_status_edit_regenerates_the_card(self):
        """#96: the ADR headers ride in the prompt and the key — an edited
        status line costs one call on the next run, an unedited one none."""
        calls = []
        runner = lambda p: calls.append(p) or self.GOOD
        self.adr("accepted")
        analyze.refresh_narratives(self.conn, self.projects, runner)
        analyze.refresh_narratives(self.conn, self.projects, runner)
        self.assertEqual(len(calls), 1)
        self.assertIn('"number": "ADR-0001"', calls[0])
        self.adr("superseded by ADR-0002")
        analyze.refresh_narratives(self.conn, self.projects, runner)
        self.assertEqual(len(calls), 2)
        self.assertIn("superseded by ADR-0002", calls[1])

    def test_gated_out_card_keeps_the_last_good_row(self):
        """#96: a card failing M3–M6 is not stored; the previous one stays."""
        self.adr("accepted")
        analyze.refresh_narratives(self.conn, self.projects, lambda p: self.GOOD)
        self.adr("superseded by ADR-0002")
        unknown_adr = json.dumps({"Standing": self.STANDING, "Now": self.NOW,
                                  "Superseded": ["OTLP listener ingest (Aug 1) → ADR-0009 (Aug 16)"]})
        analyze.refresh_narratives(self.conn, self.projects, lambda p: unknown_adr)
        self.assertEqual(self.stored(), [("p", self.GOOD, "status-v2", analyze.MODEL)])

    def test_superseded_line_tracing_to_an_adr_is_stored(self):
        self.adr("accepted")
        out = json.dumps({"Standing": self.STANDING, "Now": self.NOW, "Superseded": [
            "ADR-0001 OTLP listener ingest (Aug 1) → wire telemetry (Aug 16)"]})
        analyze.refresh_narratives(self.conn, self.projects, lambda p: out)
        self.assertEqual(self.stored(), [("p", out, "status-v2", analyze.MODEL)])

    def test_refusal_and_off_contract_not_stored(self):
        ok = {"Standing": self.STANDING, "Superseded": [], "Now": self.NOW}
        for bad in ("I don't see a ledger", None,
                    self.GOOD.replace("Standing", "Built"),                     # v1 shape
                    json.dumps({**ok, "Standing": self.STANDING[:2]}),         # M6: < 3
                    json.dumps({**ok, "Standing": ["Sunshine tomorrow", *self.STANDING[1:]]}),  # M3
                    json.dumps({**ok, "Superseded": ["Ship OTLP listener (Aug 16)"]}),  # M4: one date
                    json.dumps({**ok, "Superseded": None}),                    # #77: null group
                    json.dumps({**ok, "Now": ["OTLP listener (Aug 16)"]})):    # M5
            analyze.refresh_narratives(self.conn, self.projects, lambda p: bad)
            self.assertEqual(self.stored(), [], bad)

    def test_undeclared_project_skipped_without_a_call(self):
        (self.projects / "p" / "local-process.md").unlink()   # the master decides
        analyze.refresh_narratives(self.conn, self.projects,
                                   lambda p: self.fail("model called"))
        self.assertEqual(self.stored(), [])

    def test_eval_pin_matches_the_live_model(self):
        cases = json.loads((analyze.REPO / "eval" / "status_v2_cases.json").read_text())
        self.assertEqual(cases["model"], analyze.MODEL)
        what = json.loads((analyze.REPO / "eval" / "what_cases.json").read_text())
        self.assertEqual(what["model"], analyze.MODEL)

    def test_limit_exhaustion_propagates(self):
        def runner(p):
            raise analyze.LimitExhausted("limit")
        with self.assertRaises(analyze.LimitExhausted):
            analyze.refresh_narratives(self.conn, self.projects, runner)

    def test_status_prompt_carries_no_eval_answers(self):
        """#96: v2-p1..p5 were void because the prompt's examples quoted the
        frozen set's anchors and titles. No anchor, and no four-word run of a
        case title or ADR title, may appear in the live prompt."""
        cases = json.loads((analyze.REPO / "eval" / "status_v2_cases.json").read_text())["cases"]
        words = lambda t: re.findall(r"[a-z0-9\-]+", t.lower())

        def leaks(prompt):
            p = f" {' '.join(words(prompt))} "
            found = []
            for c in cases.values():
                anchors = [a for f in c["expected"] for a in f["anchors"]] + [
                    f if isinstance(f, str) else f["anchor"] for f in c["forbidden"]]
                found += [a for a in anchors if a and f" {' '.join(words(a))} " in p]
                for t in [t for r in c["runs"] for t in r["titles"]] + [a["title"] for a in c["adrs"]]:
                    w = words(t)
                    found += [g for g in (" ".join(w[i:i + 4]) for i in range(len(w) - 3))
                              if f" {g} " in p]
            return found
        self.assertEqual(leaks(analyze.STATUS_PROMPT), [])
        self.assertTrue(leaks("e.g. close OpenSpec"))  # the check bites


class DriftTest(DbHelpers, unittest.TestCase):
    """The schema-drift guard (issue #15): a histogram delta between record
    versions writes a breakage row and the run carries on."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.notified = []
        self.enterContext(unittest.mock.patch.object(
            analyze, "_notify", self.notified.append))

    def corpus(self, sid, version, pairs=25, strip=(), extra=None, junk=0):
        """A session of `pairs` user/assistant pairs under `version`;
        `strip` removes message-level keys from assistant records, `extra`
        adds top-level keys, `junk` appends unknown-type records."""
        recs = []
        for i in range(pairs):
            u = {**rec("user", f"{sid}u{i}", "2026-08-01T10:00:00Z", "go"),
                 "version": version, **(extra or {})}
            a = {**rec("assistant", f"{sid}a{i}", "2026-08-01T10:00:01Z",
                       [{"type": "text", "text": "ok"}],
                       usage=USAGE, model="m", id=f"{sid}m{i}"),
                 "version": version, **(extra or {})}
            for k in strip:
                del a["message"][k]
            recs += [u, a]
        recs += [{"type": "flurble"}] * junk
        write_records(self.root / "p" / f"{sid}.jsonl", recs)

    def run_pipeline(self, notify=False):
        base = Path(self.tmp.name)
        with captured_earlier():
            run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                          model_runner=StubRunner([SKIP_MD] * 20),
                          claude_dir=base / "claude", projects_dir=base / "repos",
                          notify=notify)

    def open_rows(self):
        return self.rows("SELECT * FROM breakage WHERE acknowledged_at IS NULL ORDER BY id")

    def test_thinned_contract_key_is_a_problem_breakage_and_ingest_continues(self):
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", strip=("usage",))
        self.run_pipeline(notify=True)
        rows = self.open_rows()
        self.assertEqual([(r["tier"], r["condition"], r["old_version"],
                           r["new_version"], r["key"], r["since"], r["derivers"])
                          for r in rows],
                         [("problem", 1, "2.1.1", "2.1.2", "assistant.message.usage",
                           "2026-08-01", "usage")])
        self.assertIn("usage rows may be thin", analyze.breakage_text(rows[0]))
        self.assertGreater(rows[0]["old_share"], 0.9)
        self.assertLess(rows[0]["new_share"], 0.5)
        # the run completed: both sessions analysed, statuses untouched by it
        self.assertEqual(self.session_statuses(), {"old": "done", "new": "done"})
        self.assertEqual(len(self.notified), 1)
        self.assertIn("assistant.message.usage", self.notified[0])
        # the next run, same shape: no duplicate row
        self.run_pipeline()
        self.assertEqual(len(self.open_rows()), 1)

    def test_a_key_two_derivers_read_names_both(self):
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", strip=("id",))
        self.run_pipeline()
        self.assertEqual([(r["key"], r["derivers"]) for r in self.open_rows()],
                         [("assistant.message.id", "usage, tool_events")])

    def test_resumed_session_dates_since_from_the_histogram(self):
        """ADR-0037 §2: a session opened under 2.1.1 and resumed under 2.1.2
        dates the breakage from its own first day, not from the sessions
        whose head version is 2.1.2 (there are none)."""
        self.corpus("old", "2.1.1")
        recs = []
        for i, (version, ts) in enumerate([("2.1.1", "2026-07-20T10:00:00Z")]
                                          + [("2.1.2", "2026-08-03T10:00:00Z")] * 25):
            a = {**rec("assistant", f"a{i}", ts, [{"type": "text", "text": "ok"}],
                       model="m", id=f"m{i}"), "version": version}
            recs += [{**rec("user", f"u{i}", ts, "go"), "version": version}, a]
        write_records(self.root / "p" / "resumed.jsonl", recs)
        self.run_pipeline()
        self.assertEqual([(r["key"], r["since"]) for r in self.open_rows()],
                         [("assistant.message.usage", "2026-07-20")])

    def test_otel_thinned_attribute_is_a_problem_and_an_added_one_is_silent(self):
        """ADR-0037 §4: per (service, version, event), condition 1 only."""
        import listener
        self.corpus("new", "2.1.1")  # gives the OTel session a day

        def events(version, n, **attrs):
            return {"resourceLogs": [{
                "resource": {"attributes": [
                    {"key": "service.name", "value": {"stringValue": "claude-code"}},
                    {"key": "service.version", "value": {"stringValue": version}}]},
                "scopeLogs": [{"logRecords": [{"attributes": [
                    {"key": k, "value": {"stringValue": v}} for k, v in
                    {"event.name": "api_request", "session.id": "new", **attrs}.items()]}
                    for _ in range(n)]}]}]}

        listener.init_db(self.db)
        conn = sqlite3.connect(self.db)
        with conn:
            listener.ingest_logs(events("2.1.1", 25, model="m", duration_ms="5"), conn)
            listener.ingest_logs(events("2.1.2", 25, model="m", speed="fast"), conn)
        conn.close()
        self.run_pipeline(notify=True)
        rows = self.open_rows()
        self.assertEqual([(r["tier"], r["condition"], r["source"], r["key"],
                           r["old_version"], r["new_version"], r["since"])
                          for r in rows],
                         [("problem", 1, "otel", "api_request.duration_ms",
                           "claude-code 2.1.1", "claude-code 2.1.2", "2026-08-01")])
        self.assertTrue(rows[0]["derivers"])
        self.assertEqual(len(self.notified), 1)

    def test_guard_skips_while_a_session_is_due_and_the_run_stays_ok(self):
        """ADR-0038 §3: a record captured after derivation (a hook firing
        mid-run) leaves its session due; the guard skips as designed, the
        health row stays ok, and the next run checks."""
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", strip=("usage",))
        late = self.root / "p" / "old.jsonl"
        real = analyze.derive

        def then_a_firing(conn, name, version, fn):
            real(conn, name, version, fn)
            if name == "field_histogram" and not getattr(then_a_firing, "fired", False):
                then_a_firing.fired = True
                with late.open("a") as f:
                    f.write(json.dumps(rec("user", "late", "2026-08-01T11:00:00Z", "x")) + "\n")
                analyze.capture(conn, late)

        analyze.derive = then_a_firing
        self.addCleanup(setattr, analyze, "derive", real)
        self.run_pipeline()
        self.assertEqual(self.open_rows(), [])
        [health] = self.rows("SELECT error_text FROM health WHERE source='analysis'")
        self.assertIsNone(health["error_text"])

        self.run_pipeline()
        self.assertEqual([r["condition"] for r in self.open_rows()], [1])

    def test_same_shape_under_a_new_version_is_quiet(self):
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2")
        self.run_pipeline(notify=True)
        self.assertEqual(self.open_rows(), [])
        self.assertEqual(self.notified, [])

    def test_added_top_level_keys_are_one_informational_row_and_silent(self):
        # Issue #30: a release adds several keys at once — one judgement, one row.
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", extra={"effort": "high", "agentId": "x"})
        self.run_pipeline(notify=True)
        rows = self.open_rows()
        self.assertEqual([(r["tier"], r["condition"], r["key"]) for r in rows],
                         [("informational", 2, "assistant.agentId, assistant.effort,"
                           " user.agentId, user.effort")])
        self.assertIn("4 keys are new under 2.1.2", analyze.breakage_text(rows[0]))
        self.assertEqual(self.notified, [])
        # A key first seen on a later run joins nothing: the open row stands alone.
        self.corpus("new2", "2.1.2", pairs=30, extra={"effort": "high", "agentId": "x", "mode": 1})  # mode in 30/55 > ADDED
        self.run_pipeline(notify=True)
        self.assertEqual(len(self.open_rows()), 1)

    def test_tiny_new_version_waits_for_evidence(self):
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", pairs=5, strip=("usage",))  # 10 < MIN_RECORDS
        self.run_pipeline()
        self.assertEqual(self.open_rows(), [])

    def test_acknowledge_closes_the_row_and_moves_the_baseline(self):
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", strip=("usage",))
        self.run_pipeline()
        bid = self.open_rows()[0]["id"]
        conn = analyze.init_db(self.db)
        self.assertTrue(analyze.acknowledge_breakage(conn, bid))
        self.assertFalse(analyze.acknowledge_breakage(conn, bid))  # already closed
        conn.close()
        self.assertEqual(self.open_rows(), [])
        self.run_pipeline()                              # same shape: quiet
        self.assertEqual(self.open_rows(), [])
        # a newer version with the key back compares against 2.1.2, not 2.1.1
        self.corpus("newer", "2.1.3")
        self.run_pipeline()
        self.assertEqual(self.open_rows(), [])
        # the acknowledged version is now the comparison: thinning again trips
        self.corpus("newest", "2.1.4", strip=("model",))
        self.run_pipeline()
        self.assertEqual([(r["old_version"], r["new_version"], r["key"])
                          for r in self.open_rows()],
                         [("2.1.3", "2.1.4", "assistant.message.model")])

    def test_version_line_is_logged_never_a_trigger(self):
        """The CLI's own version is one stdout line per run; it fires nothing
        — the guard reads the shape, and the command line is its only caller."""
        fake = subprocess.CompletedProcess([], 0, stdout="2.1.270 (Claude Code)\n", stderr="")
        with unittest.mock.patch.object(analyze.subprocess, "run", return_value=fake), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            analyze.cli_version_line()
        self.assertEqual(out.getvalue(), "claude --version: 2.1.270 (Claude Code)\n")
        with unittest.mock.patch.object(analyze.subprocess, "run",
                                        side_effect=FileNotFoundError), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            analyze.cli_version_line()
        self.assertEqual(out.getvalue(), "claude --version: unavailable\n")

    def test_acknowledge_command(self):
        self.corpus("old", "2.1.1")
        self.corpus("new", "2.1.2", strip=("usage",))
        self.run_pipeline()
        bid = self.open_rows()[0]["id"]
        # the CLI's main(argv) in-process; exit codes surface as SystemExit
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            analyze.main(["acknowledge-breakage", str(bid), "--db", str(self.db)])
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(self.open_rows(), [])
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as err, \
                self.assertRaises(SystemExit) as exit_:
            analyze.main(["acknowledge-breakage", "99", "--db", str(self.db)])
        self.assertEqual(exit_.exception.code, 1)
        self.assertIn("no open breakage row 99", err.getvalue())


class CrossCheckTest(DbHelpers, unittest.TestCase):
    """The input-side token cross-check (ADR-0033 §5, issue #89): per
    completed local day, OTel against transcripts over sessions both saw."""

    setUp = DriftTest.setUp
    run_pipeline = DriftTest.run_pipeline
    open_rows = DriftTest.open_rows

    def session(self, days, sid="s", n=50):
        """`n` assistant requests per day, each `per` input tokens; the
        cache halves are fixed so the input-side sum is what is compared."""
        recs = []
        for day, per in days.items():
            for i in range(n):
                ts = f"{day}T15:00:00Z"
                recs += [rec("user", f"{day}u{i}", ts, "go"),
                         rec("assistant", f"{day}a{i}", ts, [{"type": "text", "text": "ok"}],
                             model="m", id=f"{day}m{i}",
                             usage={"input_tokens": per, "output_tokens": 1,
                                    "cache_creation_input_tokens": 30,
                                    "cache_read_input_tokens": 40})]
        write_records(self.root / "p" / f"{sid}.jsonl", recs)

    def otel(self, day, n, per=100, sid="s", query_source=None):
        """`n` api_request events on `day`, each `per` input-side tokens."""
        import listener
        attrs = {"event.name": "api_request", "session.id": sid,
                 "event.timestamp": f"{day}T15:00:00Z", "input_tokens": str(per - 70),
                 "cache_read_tokens": "40", "cache_creation_tokens": "30"}
        if query_source:
            attrs["query_source"] = query_source
        listener.init_db(self.db)
        conn = sqlite3.connect(self.db)
        with conn:
            listener.ingest_logs({"resourceLogs": [{"scopeLogs": [{"logRecords": [
                {"attributes": [{"key": k, "value": {"stringValue": v}}
                                for k, v in attrs.items()]}] * n}]}]}, conn)
        conn.close()

    def cross_rows(self):
        return [(r["tier"], r["day"]) for r in self.open_rows() if r["condition"] == 4]

    def test_a_6_percent_gap_writes_one_row_and_4_percent_none(self):
        # OTel 100 a request; transcripts 94 (6% short) and 96 (4% short)
        self.session({"2026-08-01": 94 - 70, "2026-08-02": 96 - 70})
        self.otel("2026-08-01", 50)
        self.otel("2026-08-02", 50)
        self.run_pipeline()
        self.assertEqual(self.cross_rows(), [("problem", "2026-08-01")])
        self.assertIn("2026-08-01", analyze.breakage_text(self.open_rows()[0]))
        self.run_pipeline()  # one row per day, never a second
        self.assertEqual(self.cross_rows(), [("problem", "2026-08-01")])

    def test_a_day_under_the_floor_and_the_current_day_are_never_checked(self):
        today = time.strftime("%Y-%m-%d")
        self.session({"2026-08-01": 24, today: 24}, n=49)
        self.otel("2026-08-01", 49)
        self.otel(today, 49)
        self.otel(today, 1)  # today clears the floor; it is still not checked
        self.run_pipeline()
        self.assertEqual(self.cross_rows(), [])

    def test_denylisted_side_requests_are_excluded_and_a_new_side_source_trips(self):
        self.session({"2026-08-01": 30})  # 100 a request: matches OTel exactly
        self.otel("2026-08-01", 50)
        for source in ("prompt_suggestion", "generate_session_title", "web_search_tool",
                       "web_fetch_apply", "away_summary", "agent_summary"):
            self.otel("2026-08-01", 5, per=1000, query_source=source)
        self.run_pipeline()
        self.assertEqual(self.cross_rows(), [])
        self.otel("2026-08-01", 5, per=1000, query_source="brand_new_side_request")
        self.run_pipeline()
        self.assertEqual(self.cross_rows(), [("problem", "2026-08-01")])

    def test_a_session_the_listener_missed_that_day_is_left_out(self):
        # t has transcript usage on 08-01 but OTel only on 08-02 (listener
        # down on 08-01): 08-01 compares s alone, which agrees
        self.session({"2026-08-01": 30}, sid="s")
        self.session({"2026-08-01": 30, "2026-08-02": 30}, sid="t")
        self.otel("2026-08-01", 50, sid="s")
        self.otel("2026-08-02", 50, sid="t")
        self.run_pipeline()
        self.assertEqual(self.cross_rows(), [])

    def test_acknowledging_closes_that_day_and_shifts_no_baseline(self):
        self.session({"2026-08-01": 24})
        self.otel("2026-08-01", 50)
        self.run_pipeline()
        [row] = self.open_rows()
        conn = sqlite3.connect(self.db)
        self.assertTrue(analyze.acknowledge_breakage(conn, row["id"]))
        conn.close()
        # a later day drifts by the same 6%: still a trip at the frozen
        # threshold, and the acknowledged day stays closed
        self.session({"2026-08-01": 24, "2026-08-02": 24})
        self.otel("2026-08-02", 50)
        self.run_pipeline()
        self.assertEqual(self.cross_rows(), [("problem", "2026-08-02")])
        self.assertEqual(len(self.rows("SELECT 1 FROM breakage WHERE condition=4")), 2)


class SectionDrift(unittest.TestCase):
    """Ticket #81: the prompt names the audit sections as prose
    (uninterpolated by design, #79) — detect drift from the SECTIONS
    vocabulary rather than prevent it."""

    def test_active_what_prompt_names_every_section(self):
        for name in analyze.SECTIONS:
            self.assertIn(f"**{name}:**", analyze.WHAT_PROMPT)


class CompactionTest(DbHelpers, unittest.TestCase):
    """Compaction at the raw limit (ADR-0034, ADR-0038 §1, ticket #92)."""

    OLD = "2026-08-01T10:00:00Z"  # past a 90-day limit from any run after 2026-10-30

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.proj = self.root / "test-project"

    def write(self, sid, ts):
        write_records(self.proj / f"{sid}.jsonl", [
            rec("user", f"{sid}-0", ts, "do the thing"),
            rec("assistant", f"{sid}-1", ts, [{"type": "text", "text": "done"}],
                id=f"m-{sid}", model="claude-x", usage=USAGE)])

    def run_pipeline(self, days, runner):
        base = Path(self.tmp.name)
        with unittest.mock.patch.dict(os.environ, {"HINDSIGHT_RAW_DAYS": days}), \
                captured_earlier(), contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                         model_runner=runner, claude_dir=base / "claude",
                         projects_dir=base / "repos")

    def raw(self, sid):
        return self.rows("SELECT rowid FROM raw_records WHERE session_id=?", (sid,))

    def provenance(self, sid):
        return {t: [r["provenance"] for r in self.rows(
                    f"SELECT provenance FROM {t} WHERE session_id=?", (sid,))]
                for t in ("records_index", "usage")}

    def health(self):
        [row] = self.rows("SELECT * FROM health WHERE source='analysis'")
        return row, json.loads(row["detail"])

    def caches(self, sid):
        return [*self.work.glob(f"extracts/{sid}.*"),
                *self.work.glob(f"{analyze.PROMPT_VERSION}/{sid}.*")]

    def test_a_done_session_past_the_limit_is_compacted_and_its_rows_survive(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.write("sess-old", self.OLD)
        self.write("sess-new", recent.replace("+00:00", "Z"))
        self.run_pipeline("90", StubRunner([ENTRY_A, ENTRY_A]))

        self.assertEqual(self.raw("sess-old"), [])
        self.assertTrue(self.raw("sess-new"))
        self.assertEqual(self.provenance("sess-old"),
                         {"records_index": ["compacted"] * 2, "usage": ["compacted"]})
        self.assertEqual(self.provenance("sess-new"),
                         {"records_index": ["raw"] * 2, "usage": ["raw"]})
        self.assertEqual(self.caches("sess-old"), [])
        self.assertTrue(self.caches("sess-new"))
        self.assertIn("sess-old", self.audit_rows())
        self.assertEqual(self.session_statuses()["sess-old"], "done")
        self.assertEqual(self.rows(
            f"SELECT {analyze.session_day('s')} AS day FROM sessions s WHERE id='sess-old'"),
            [{"day": "2026-08-01"}])
        row, detail = self.health()
        self.assertIsNone(row["error_text"])
        self.assertEqual(detail, {"raw_days": 90, "held": 0})

        # The transcript is still on disk: the sweep must not capture it
        # again, and a deriver version bump must leave its rows frozen.
        bump = analyze.USAGE_VERSION
        analyze.USAGE_VERSION = bump + 1
        self.addCleanup(setattr, analyze, "USAGE_VERSION", bump)
        self.run_pipeline("90", StubRunner([]))

        self.assertEqual(self.raw("sess-old"), [])
        self.assertEqual(self.provenance("sess-old"),
                         {"records_index": ["compacted"] * 2, "usage": ["compacted"]})
        self.assertEqual(self.provenance("sess-new")["usage"], ["raw"])

    def test_a_due_or_pending_session_past_the_limit_is_held_and_reported(self):
        self.write("sess-a", self.OLD)  # audited, but a deriver still has it due
        self.write("sess-b", self.OLD)  # derived, but the what-pass paused on it
        real = analyze.derive_usage

        def poisoned(conn, sid, records):
            if sid == "sess-a":
                raise ValueError("poison")
            return real(conn, sid, records)

        analyze.derive_usage = poisoned
        self.addCleanup(setattr, analyze, "derive_usage", real)
        self.run_pipeline("90", StubRunner([ENTRY_A, LimitExhausted("limit")]))

        self.assertEqual(self.session_statuses(), {"sess-a": "done", "sess-b": "pending"})
        self.assertTrue(self.raw("sess-a"))
        self.assertTrue(self.raw("sess-b"))
        self.assertEqual(self.provenance("sess-b")["records_index"], ["raw"] * 2)
        row, detail = self.health()
        self.assertNotIn("compaction", row["error_text"])
        self.assertEqual(detail, {"raw_days": 90, "held": 2})

    def test_zero_never_compacts_and_a_bad_value_compacts_nothing_and_errors(self):
        self.write("sess-a", self.OLD)
        self.run_pipeline("0", StubRunner([ENTRY_A]))
        self.assertTrue(self.raw("sess-a"))
        row, detail = self.health()
        self.assertIsNone(row["error_text"])
        self.assertEqual(detail, {"raw_days": 0, "held": 0})

        for bad in ("-1", "abc"):
            with self.subTest(bad=bad):
                self.run_pipeline(bad, StubRunner([]))
                self.assertTrue(self.raw("sess-a"))
                row, detail = self.health()
                self.assertIn("compaction", row["error_text"])
                self.assertIn("HINDSIGHT_RAW_DAYS", row["error_text"])
                self.assertEqual(row["failing_since"] is not None, True)
                self.assertEqual(detail, {"raw_days": None, "held": None})

        self.run_pipeline("90", StubRunner([]))  # the same session was eligible all along
        self.assertEqual(self.raw("sess-a"), [])

    def test_a_large_limit_never_compacts(self):
        self.write("sess-a", self.OLD)
        for days in ("1000000", "999999999", "10000000000"):
            with self.subTest(days=days):
                self.run_pipeline(days, StubRunner([ENTRY_A]))
                self.assertTrue(self.raw("sess-a"))
                row, detail = self.health()
                self.assertIsNone(row["error_text"])
                self.assertEqual(detail, {"raw_days": int(days), "held": 0})

    def test_a_compacted_session_resumed_keeps_its_audit_entry(self):
        old = [rec("user", "r-0", self.OLD, "do the thing"),
               rec("assistant", "r-1", self.OLD, [{"type": "text", "text": "done"}],
                   id="m-r", model="claude-x", usage=USAGE)]
        write_records(self.proj / "sess-r.jsonl", old)
        self.run_pipeline("90", StubRunner([ENTRY_A]))
        self.assertEqual(self.raw("sess-r"), [])
        before = self.audit_rows()["sess-r"]

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        tail = [rec("user", f"r-{i}", recent.replace("+00:00", "Z"), "more " * 20)
                for i in range(2, 8)]
        write_records(self.proj / "sess-r.jsonl", old + tail)
        runner = StubRunner([ENTRY_B])
        self.run_pipeline("90", runner)

        self.assertEqual(runner.calls, [])
        self.assertEqual(self.audit_rows()["sess-r"], before)
        self.assertEqual(self.session_statuses()["sess-r"], "done")

    def test_a_compacted_session_resumed_with_a_short_tail_derives_the_tail_once(self):
        # raw_records reuses the rowids compaction freed: a tail shorter than
        # the compacted records lands at or below the session's old state
        old = [rec("user", f"t-{i}", self.OLD, "go") if i % 2 == 0 else
               rec("assistant", f"t-{i}", self.OLD, [{"type": "text", "text": "ok"}],
                   id=f"m-t{i}", model="claude-x", usage=USAGE) for i in range(10)]
        write_records(self.proj / "sess-t.jsonl", old)
        self.run_pipeline("90", StubRunner([ENTRY_A]))
        self.assertEqual(self.raw("sess-t"), [])
        frozen = self.rows("SELECT * FROM usage WHERE session_id='sess-t'")
        self.assertEqual(len(frozen), 5)

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        recent = recent.replace("+00:00", "Z")
        tail = [rec("user", "t-10", recent, "more"),
                rec("assistant", "t-11", recent, [{"type": "text", "text": "ok"}],
                    id="m-t11", model="claude-x", usage=USAGE)]
        write_records(self.proj / "sess-t.jsonl", old + tail)
        for _ in range(3):
            self.run_pipeline("90", StubRunner([]))

            self.assertEqual(len(self.raw("sess-t")), 2)  # recent: not yet past the limit
            self.assertEqual(self.rows("SELECT * FROM usage WHERE session_id='sess-t'"
                                       " AND provenance='compacted'"), frozen)
            self.assertEqual(self.rows("SELECT message_id FROM usage WHERE session_id="
                                       "'sess-t' AND provenance='raw'"),
                             [{"message_id": "m-t11"}])
            self.assertEqual(self.provenance("sess-t")["records_index"],
                             ["compacted"] * 10 + ["raw"] * 2)

    def test_a_session_with_an_open_rewrite_breakage_is_held(self):
        records = [rec("user", "w-0", self.OLD, "do the thing"),
                   rec("assistant", "w-1", self.OLD, [{"type": "text", "text": "done"}],
                       id="m-w", model="claude-x", usage=USAGE)]
        write_records(self.proj / "sess-w.jsonl", records)
        self.run_pipeline("0", StubRunner([ENTRY_A]))
        records[1]["message"]["content"][0]["text"] = "DONE"
        records.append(rec("user", "w-2", self.OLD, "and more"))  # grown, so capture checks
        write_records(self.proj / "sess-w.jsonl", records)
        self.run_pipeline("90", StubRunner([]))

        self.assertTrue(self.rows("SELECT 1 FROM breakage WHERE condition=6"
                                  " AND session_id='sess-w' AND acknowledged_at IS NULL"))
        self.assertTrue(self.raw("sess-w"))
        self.assertEqual(self.health()[1], {"raw_days": 90, "held": 1})


class JobListTest(DbHelpers, unittest.TestCase):
    """The analysis run as an ordered job list (ADR-0038, ticket #85): each
    job fails alone, one `analysis` health row, single-flight."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.claude = base / "claude"
        self.claude.mkdir()
        (self.claude / "CLAUDE.md").write_text("# rules")
        self.repos = base / "repos"
        self.repos.mkdir()
        write_transcript(self.root / "test-project" / "sess-a.jsonl",
                          [("user", "task a"), ("assistant", "done a")])

    def run_pipeline(self, model_runner):
        with captured_earlier():
            run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                          model_runner=model_runner,
                          claude_dir=self.claude, projects_dir=self.repos)

    def patch(self, name, fn):
        orig = getattr(analyze, name)
        setattr(analyze, name, fn)
        self.addCleanup(setattr, analyze, name, orig)

    def health(self):
        return self.rows("SELECT * FROM health WHERE source='analysis'")

    def test_failing_job_runs_the_rest_and_errors_the_row_naming_it(self):
        self.patch("capture_backstop",
                   lambda *a: (_ for _ in ()).throw(TypeError("bad shape")))
        with contextlib.redirect_stderr(io.StringIO()):
            self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(self.session_statuses()["sess-a"], "done")
        self.assertTrue(self.rows("SELECT * FROM sunk_cost"),
                        "the sunk-cost scan never ran after the backstop failed")
        [row] = self.health()
        self.assertIsNotNone(row["last_error"])
        self.assertIsNone(row["last_success"])
        self.assertEqual(row["failing_since"], row["last_error"])
        self.assertTrue(row["last_error"].endswith("Z"))
        self.assertIn("backstop", row["error_text"])
        self.assertIn("bad shape", row["error_text"])
        self.assertNotIn("sunk-cost", row["error_text"])

    def test_migration_failure_runs_nothing_else(self):
        self.db.write_bytes(b"not a database" * 100)
        stub = StubRunner([ENTRY_A])
        with self.assertRaises(sqlite3.DatabaseError):
            self.run_pipeline(stub)
        self.assertEqual(stub.calls, [])
        self.assertFalse(self.work.exists(), "a job ran after the migration failed")

    def test_limit_pause_skips_the_narrative_and_leaves_the_row_ok(self):
        narratives = []
        self.patch("refresh_narratives", lambda *a: narratives.append(a))
        self.run_pipeline(StubRunner([LimitExhausted("usage limit reached")]))
        self.assertEqual(narratives, [])
        [row] = self.health()
        self.assertIsNotNone(row["last_success"])
        self.assertTrue(row["last_success"].endswith("Z"))
        self.assertIsNone(row["last_error"])
        self.assertIsNone(row["failing_since"])

    def test_success_after_an_error_clears_failing_since(self):
        self.patch("scan_sunk_cost",
                   lambda *a: (_ for _ in ()).throw(OSError("gone")))
        with contextlib.redirect_stderr(io.StringIO()):
            self.run_pipeline(StubRunner([ENTRY_A]))
        analyze.scan_sunk_cost = sunk_cost_scan
        self.run_pipeline(StubRunner([]))
        [row] = self.health()
        self.assertIsNotNone(row["last_success"])
        self.assertIsNone(row["failing_since"])

    def test_second_run_while_one_holds_the_lock_exits_at_once(self):
        import threading
        started, release = threading.Event(), threading.Event()

        def blocking_runner(prompt):
            started.set()
            release.wait(30)
            return ENTRY_A

        first = threading.Thread(target=self.run_pipeline, args=(blocking_runner,))
        first.start()
        self.addCleanup(first.join)
        self.addCleanup(release.set)
        self.assertTrue(started.wait(30), "the first run never reached the model")
        second = StubRunner([])
        err = io.StringIO()
        t0 = time.monotonic()
        with contextlib.redirect_stderr(err):
            self.run_pipeline(second)  # returns: exit 0 from the CLI
        self.assertLess(time.monotonic() - t0, 5)
        self.assertEqual(second.calls, [])
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1)
        self.assertEqual(self.health(), [], "the second run wrote a health row")
        release.set()
        first.join()
        self.assertEqual(len(self.health()), 1)


class ProjectNameTest(unittest.TestCase):
    def test_strips_the_encoded_projects_dir_of_any_user(self):
        ws = Path("/home/some.one/Work Space")
        self.assertEqual(analyze.project_name("-home-some-one-Work-Space-hindsight", ws), "hindsight")
        self.assertEqual(analyze.project_name("-tmp-elsewhere", ws), "-tmp-elsewhere")


if __name__ == "__main__":
    unittest.main()
