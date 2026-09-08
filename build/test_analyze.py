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
import sqlite3
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import analyze
import listener
from analyze import LimitExhausted, run_analysis
from test_helpers import (DbHelpers, ENTRY_A, ENTRY_B, FIXTURE_TURNS,
                          MERGED_ENTRY, REFUSAL_MD, SKIP_MD, StubRunner,
                          USAGE, _backdate, big_turns, rec, write_records,
                          write_transcript)


class AnalyzeTest(DbHelpers, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.proj = self.root / "test-project"

    def run_pipeline(self, model_runner):
        # Fixture backstop dirs (may not exist): the run must never touch
        # the real ~/.claude or project repos from a test.
        base = Path(self.tmp.name)
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

    def test_live_session_left_pending_not_extracted(self):
        """Ticket #29, the guard: a transcript still being written is not
        extracted or substrate-scanned; the session waits for the next run."""
        path = self.proj / "sess-hot.jsonl"
        write_transcript(path, FIXTURE_TURNS)
        now = time.time()
        os.utime(path, (now, now))  # still being written
        self.run_pipeline(StubRunner([]))  # zero actions: no model call happens

        self.assertEqual(self.session_statuses()["sess-hot"], "pending")
        self.assertFalse(list((self.work / "extracts").glob("sess-hot.*")))
        self.assertIsNone(self.rows(
            "SELECT skipped_records FROM sessions")[0]["skipped_records"])

        _backdate(path)  # session went quiet: next run processes it normally
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

    def test_live_resumed_session_keeps_its_substrate(self):
        """Ticket #76: a `done` session resumed and still being written must
        not be wiped. `fill_substrate` skips a live transcript (ticket #29),
        so the wipe would leave the session with zero substrate rows for the
        rest of the run — it waits instead, and tops up once quiet."""
        path = self._resume("sess-hotresume", [
            rec("assistant", "a1", "2026-08-01T10:10:00Z",
                [{"type": "text", "text": "a bit more"}],
                usage=USAGE, model="test-model", id="msg-1")])
        now = time.time()
        os.utime(path, (now, now))  # still being written
        self.run_pipeline(StubRunner([]))
        self.assertEqual(len(self.rows(
            "SELECT * FROM usage WHERE session_id='sess-hotresume'")), 1,
            "live session's substrate wiped with nothing left to refill it")

        _backdate(path)  # went quiet: the next run tops it up
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

    def test_pruned_unextracted_session_is_lost_and_never_retried(self):
        """Ticket #78: no transcript and no cached extract — terminal, not
        retryable. The queue would otherwise never drain."""
        write_transcript(self.proj / "sess-vanish.jsonl",
                          [("user", "task"), ("assistant", "done")])
        conn = analyze.init_db(self.db)
        analyze.sync_sessions(conn, self.root)
        conn.close()
        (self.proj / "sess-vanish.jsonl").unlink()  # gone before extraction runs

        self.run_pipeline(StubRunner([]))  # no model call
        self.assertEqual(self.session_statuses()["sess-vanish"], "lost")
        self.assertNotIn("sess-vanish", self.audit_rows())

        self.run_pipeline(StubRunner([]))  # never selected again
        self.assertEqual(self.session_statuses()["sess-vanish"], "lost")

    def test_pruned_session_with_cached_extract_proceeds_to_model_pass(self):
        write_transcript(self.proj / "sess-cached.jsonl",
                          [("user", "task"), ("assistant", "done")])
        conn = analyze.init_db(self.db)
        analyze.sync_sessions(conn, self.root)
        conn.close()
        analyze.extract_session(self.work, "sess-cached",
                                self.proj / "sess-cached.jsonl")
        (self.proj / "sess-cached.jsonl").unlink()

        self.run_pipeline(StubRunner([ENTRY_A]))
        self.assertEqual(self.session_statuses()["sess-cached"], "done")
        self.assertEqual(self.audit_rows()["sess-cached"]["markdown"], ENTRY_A)

    def test_reaudit_pending_session_pruned_keeps_entry_as_done(self):
        """A done session queued for re-audit (ADR-0013) whose transcript
        is then pruned still has its entry — it stands, prefix-semantic."""
        conn = analyze.init_db(self.db)
        conn.execute("INSERT INTO sessions (id, project, transcript_path, date,"
                     " status) VALUES ('sess-re', 'p', '/gone', '2026-08-01', 'pending')")
        conn.execute("INSERT INTO audit (session_id, project, date, skip, markdown,"
                     " prompt_version, model) VALUES ('sess-re', 'p', '2026-08-01',"
                     " 0, ?, 'v', 'm')", (ENTRY_A,))
        analyze.classify_and_extract(conn, self.work)
        self.assertEqual(dict(conn.execute("SELECT id, status FROM sessions")),
                         {"sess-re": "done"})
        conn.close()

    def test_unextractable_transcript_stays_partial(self):
        """ExtractionFailed on a path that exists is retryable — only
        absence is terminal (ticket #78)."""
        conn = analyze.init_db(self.db)
        bad = self.proj / "sess-bad.jsonl"
        bad.mkdir(parents=True)  # exists, but extract.py cannot read it
        _backdate(bad)
        conn.execute("INSERT INTO sessions (id, project, transcript_path, date,"
                     " status) VALUES ('sess-bad', 'p', ?, '2026-08-01', 'partial')",
                     (str(bad),))
        analyze.classify_and_extract(conn, self.work)
        self.assertEqual(dict(conn.execute("SELECT id, status FROM sessions")),
                         {"sess-bad": "partial"})
        conn.close()

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
        try:
            self.assertIsNone(analyze.default_model_runner("prompt"))
        finally:
            analyze.subprocess.run = orig

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
    its SessionStart hook row (ticket #4, ADR-0018), driven through the
    analysis-run entrypoint over a fixture transcript root and the shared
    otel_events table the listener also writes to."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "projects"
        self.db = base / "hindsight.db"
        self.work = base / "analysis"
        self.proj = self.root / "test-project"

    def run_pipeline(self, model_runner):
        base = Path(self.tmp.name)
        run_analysis(root=self.root, db_path=self.db, work_dir=self.work,
                      model_runner=model_runner,
                      claude_dir=base / "claude", projects_dir=base / "repos")

    def seed_hook_row(self, sid, attributes_json):
        conn = analyze.init_db(self.db)
        conn.executescript(listener.SCHEMA)
        conn.execute(
            "INSERT INTO otel_events (event_name, session_id, timestamp, attributes)"
            " VALUES ('hindsight.hook', ?, '2026-08-01T09:00:00Z', ?)",
            (sid, attributes_json))
        conn.commit()
        conn.close()

    def identity_row(self, sid):
        return next(r for r in self.rows(
            "SELECT id, folder_identity, attribution_source FROM sessions")
            if r["id"] == sid)

    def test_sync_fills_identity_and_source_from_session_start_row(self):
        write_transcript(self.proj / "sess-id.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])
        self.seed_hook_row(
            "sess-id",
            '{"hook.event": "SessionStart", "folder.identity": "424242"}')

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-id")
        self.assertEqual(row["folder_identity"], 424242)
        self.assertEqual(row["attribution_source"], "hook")

    def test_sync_leaves_session_name_only_without_a_hook_row(self):
        write_transcript(self.proj / "sess-noid.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-noid")
        self.assertIsNone(row["folder_identity"])
        self.assertIsNone(row["attribution_source"])

    def test_sync_falls_through_a_failed_session_start_firing_to_a_later_one(self):
        # A resumed session can fire SessionStart twice; the first firing's
        # stat failed (no folder.identity), the second succeeded — the
        # valid one must still be picked up, not hidden by the first.
        write_transcript(self.proj / "sess-resumed.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])
        conn = analyze.init_db(self.db)
        conn.executescript(listener.SCHEMA)
        conn.executemany(
            "INSERT INTO otel_events (event_name, session_id, timestamp, attributes)"
            " VALUES ('hindsight.hook', ?, ?, ?)",
            [("sess-resumed", "2026-08-01T09:00:00Z",
              '{"hook.event": "SessionStart"}'),
             ("sess-resumed", "2026-08-01T09:05:00Z",
              '{"hook.event": "SessionStart", "folder.identity": "99"}')])
        conn.commit()
        conn.close()

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-resumed")
        self.assertEqual(row["folder_identity"], 99)
        self.assertEqual(row["attribution_source"], "hook")

    def test_sync_ignores_non_session_start_hook_rows(self):
        write_transcript(self.proj / "sess-stop.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])
        self.seed_hook_row(
            "sess-stop", '{"hook.event": "Stop", "hook.cpu_ms": 5}')

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-stop")
        self.assertIsNone(row["folder_identity"])
        self.assertIsNone(row["attribution_source"])

    def test_sync_without_otel_table_leaves_session_name_only(self):
        # Ticket #50: a db the listener has never touched has no otel
        # tables at all — sync must not raise.
        write_transcript(self.proj / "sess-nolistener.jsonl",
                          [("user", "add a feature"), ("assistant", "added")])

        self.run_pipeline(StubRunner([ENTRY_A]))

        row = self.identity_row("sess-nolistener")
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
                conn.execute("PRAGMA user_version").fetchone()[0], 6)
        finally:
            conn.close()
        row = self.identity_row("sess-old")
        self.assertIsNone(row["folder_identity"])
        self.assertIsNone(row["attribution_source"])


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
    """Ticket #57 / ADR-0009: the analysis run observes each project's
    workspace folder and stores the observation for the server to render."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.projects = Path(self.tmp.name) / "Claude"
        (self.projects / "my-os" / "my-logs").mkdir(parents=True)
        (self.projects / "career-ops").mkdir()
        self.db = Path(self.tmp.name) / "h.db"

    def observe(self, *projects):
        conn = analyze.init_db(self.db)
        try:
            conn.executemany(
                "INSERT OR IGNORE INTO sessions (id, project, transcript_path)"
                " VALUES (?, ?, 'x')", [(p, p) for p in projects])
            analyze.observe_presence(conn, self.projects)
        finally:
            conn.close()
        return {r["project"]: r["present"]
                for r in self.rows("SELECT * FROM project_presence")}

    def test_dash_ambiguous_name_resolves_through_a_subdirectory(self):
        """`my-os-my-logs` is a session run in `my-os/my-logs`, not a project
        called that — one decoding of its dashes exists, so it is present."""
        self.assertTrue(analyze.folder_present(self.projects, "my-os-my-logs"))
        self.assertTrue(analyze.folder_present(self.projects, "career-ops"))
        self.assertFalse(analyze.folder_present(self.projects, "career-ops-CLI"))
        self.assertFalse(analyze.folder_present(self.projects, "my-logs"))

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
            {r["project"]: r["present"]
             for r in self.rows("SELECT * FROM project_presence")}, before)

    def test_recreated_folder_returns_at_the_next_run(self):
        self.assertEqual(self.observe("gone")["gone"], 0)
        (self.projects / "gone").mkdir()
        self.assertEqual(self.observe("gone")["gone"], 1,
                         "presence is rewritten each run, not accreted")


class NightlyTest(unittest.TestCase):
    """The launchd nightly is a scheduled *invocation* of the on-demand
    command, not a background process (ADR-0001 amendment)."""

    def test_nightly_plist_is_a_calendar_job_invoking_this_script(self):
        import plistlib
        d = plistlib.loads(analyze.nightly_plist().encode())
        self.assertEqual(d["Label"], "com.hindsight.nightly")
        self.assertEqual(d["StartCalendarInterval"], {"Hour": 3, "Minute": 0})
        self.assertTrue(d["ProgramArguments"][-1].endswith("analyze.py"))
        self.assertNotIn("KeepAlive", d)  # scheduled invocation, not a daemon
        # the installing shell's PATH is baked in so `claude` resolves under launchd
        self.assertEqual(d["EnvironmentVariables"]["PATH"], os.environ["PATH"])


class NarrativeTest(DbHelpers, unittest.TestCase):
    """The status-narrative pass (ADR-0012, ticket #68): ledger-keyed,
    write-time gated by eval/score.py's contract floors, never on read."""
    GOOD = json.dumps({"Built": ["Ship OTLP listener and wire telemetry (Aug 16)"],
                       "Reversed": [], "Now": ["Build, since Aug 16: OTLP listener"]})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "h.db"
        self.projects = Path(self.tmp.name) / "projects"
        (self.projects / "p" / ".claude").mkdir(parents=True)
        (self.projects / "p" / ".claude" / "my-process.md").write_text(
            "---\nstages:\n  - name: Build\n    skills: [tdd]\n---\n")
        self.conn = analyze.init_db(self.db)
        self.conn.execute("INSERT INTO sessions (id, project, transcript_path, date, status)"
                          " VALUES ('s1', 'p', '/x', '2026-08-16', 'done')")
        self.conn.execute("INSERT INTO audit VALUES ('s1', 'p', '2026-08-16', 0,"
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
        self.assertEqual(self.stored(), [("p", self.GOOD, analyze.STATUS_VERSION, analyze.MODEL)])
        self.assertIn('"stage": "Build"', calls[0])
        analyze.refresh_narratives(self.conn, self.projects, runner)
        self.assertEqual(len(calls), 1)  # unchanged ledger: no second call

    def test_refusal_and_off_contract_not_stored(self):
        for bad in ("I don't see a ledger", '{"Built": ["OTLP listener, Aug 16"]}',
                    json.dumps({"Built": ["Sunshine tomorrow"], "Reversed": [],
                                "Now": ["Build, since Aug 16: listener"]}), None,
                    # ticket #77: a null group — the shape the prompt invites,
                    # since "nothing reversed" is the common case. Judged
                    # off-contract, never raised.
                    json.dumps({"Built": ["Ship OTLP listener and wire telemetry (Aug 16)"],
                                "Reversed": None,
                                "Now": ["Build, since Aug 16: OTLP listener"]}),
                    json.dumps({"Built": "Ship OTLP listener (Aug 16)", "Reversed": [],
                                "Now": ["Build, since Aug 16: OTLP listener"]})):
            analyze.refresh_narratives(self.conn, self.projects, lambda p: bad)
            self.assertEqual(self.stored(), [], bad)

    def test_undeclared_project_skipped_without_a_call(self):
        (self.projects / "p" / ".claude" / "my-process.md").unlink()
        analyze.refresh_narratives(self.conn, self.projects,
                                   lambda p: self.fail("model called"))
        self.assertEqual(self.stored(), [])

    def test_eval_pin_matches_the_live_model(self):
        cases = json.loads((analyze.REPO / "eval" / "cases.json").read_text())
        self.assertEqual(cases["model"], analyze.MODEL)

    def test_limit_exhaustion_propagates(self):
        def runner(p):
            raise analyze.LimitExhausted("limit")
        with self.assertRaises(analyze.LimitExhausted):
            analyze.refresh_narratives(self.conn, self.projects, runner)


class SectionDrift(unittest.TestCase):
    """Ticket #81: the prompt names the audit sections as prose
    (uninterpolated by design, #79) — detect drift from the SECTIONS
    vocabulary rather than prevent it."""

    def test_active_what_prompt_names_every_section(self):
        for name in analyze.SECTIONS:
            self.assertIn(f"**{name}:**", analyze.WHAT_PROMPT)


if __name__ == "__main__":
    unittest.main()
